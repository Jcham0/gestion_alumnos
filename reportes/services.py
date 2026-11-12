"""Servicios de importación y validación de datos de reportes."""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import IO

import pandas as pd
from django.core.exceptions import ValidationError
from django.db.models import CharField, F, Value
from django.db.models.functions import Concat
from django.utils import timezone

from academico.models import Alumno, Asignatura, Matricula, Nota


COLUMNAS_REQUERIDAS = (
    'email_alumno',
    'codigo_asignatura',
    'evaluacion',
    'valor',
)
COLUMNAS_DATAFRAME_NOTAS = (
    'alumno',
    'asignatura',
    'evaluacion',
    'valor',
    'anio',
)


def obtener_dataframe_notas(
    asignatura_id: int | None = None,
    anio: str | None = None,
) -> pd.DataFrame:
    """Obtiene las notas como DataFrame y aplica filtros opcionales."""
    notas = Nota.objects.order_by()
    if asignatura_id is not None:
        notas = notas.filter(matricula__asignatura_id=asignatura_id)
    if anio:
        notas = notas.filter(matricula__anio_academico=anio)

    filas = notas.values(
        'evaluacion',
        'valor',
        alumno=Concat(
            F('matricula__alumno__apellidos'),
            Value(', '),
            F('matricula__alumno__nombre'),
            output_field=CharField(),
        ),
        asignatura=Concat(
            F('matricula__asignatura__codigo'),
            Value(' - '),
            F('matricula__asignatura__nombre'),
            output_field=CharField(),
        ),
        anio=F('matricula__anio_academico'),
    ).order_by('alumno', 'asignatura', 'anio', 'evaluacion')
    dataframe = pd.DataFrame.from_records(
        filas,
        columns=COLUMNAS_DATAFRAME_NOTAS,
    )
    if not dataframe.empty:
        dataframe['valor'] = pd.to_numeric(dataframe['valor'])
        dataframe['evaluacion'] = dataframe['evaluacion'].replace(
            dict(Nota.TipoEvaluacion.choices)
        )
    return dataframe


def _validar_dataframe_notas(dataframe: pd.DataFrame) -> None:
    """Comprueba que el DataFrame incluye las columnas de notas requeridas."""
    faltantes = set(COLUMNAS_DATAFRAME_NOTAS) - set(dataframe.columns)
    if faltantes:
        raise ValueError(
            'Faltan columnas requeridas: ' + ', '.join(sorted(faltantes))
        )


def calcular_media_por_asignatura(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Calcula la media de las notas agrupadas por asignatura."""
    _validar_dataframe_notas(dataframe)
    return (
        dataframe.groupby('asignatura', as_index=False)
        .agg(media=('valor', 'mean'))
        .sort_values('asignatura')
        .reset_index(drop=True)
    )


def calcular_porcentaje_aprobados(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Calcula el porcentaje de notas aprobadas por asignatura."""
    _validar_dataframe_notas(dataframe)
    resultado = dataframe.groupby('asignatura', as_index=False).agg(
        total=('valor', 'size'),
        aprobados=('valor', lambda valores: valores.ge(5).sum()),
    )
    resultado['porcentaje_aprobados'] = (
        resultado['aprobados'] / resultado['total'] * 100
    )
    return resultado.sort_values('asignatura').reset_index(drop=True)


def obtener_ranking_alumnos(
    dataframe: pd.DataFrame,
    cantidad: int = 10,
) -> pd.DataFrame:
    """Devuelve los N alumnos con mayor media de notas."""
    _validar_dataframe_notas(dataframe)
    if cantidad < 1:
        raise ValueError('La cantidad debe ser mayor que cero.')
    return (
        dataframe.groupby('alumno', as_index=False)
        .agg(media=('valor', 'mean'), cantidad_notas=('valor', 'size'))
        .sort_values(['media', 'alumno'], ascending=[False, True])
        .head(cantidad)
        .reset_index(drop=True)
    )


def detectar_valores_atipicos_iqr(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Devuelve las notas fuera de 1,5 veces el rango intercuartílico."""
    _validar_dataframe_notas(dataframe)
    if dataframe.empty:
        return dataframe.copy()

    primer_cuartil = dataframe['valor'].quantile(0.25)
    tercer_cuartil = dataframe['valor'].quantile(0.75)
    rango_intercuartilico = tercer_cuartil - primer_cuartil
    limite_inferior = primer_cuartil - 1.5 * rango_intercuartilico
    limite_superior = tercer_cuartil + 1.5 * rango_intercuartilico
    return dataframe.loc[
        dataframe['valor'].lt(limite_inferior)
        | dataframe['valor'].gt(limite_superior)
    ].reset_index(drop=True)


def obtener_dataframe_boletin(alumno_id: int) -> pd.DataFrame:
    """Obtiene las notas y medias por asignatura y curso de un alumno."""
    columnas = (
        'alumno',
        'asignatura',
        'anio',
        'evaluacion',
        'valor',
        'fecha',
        'media_asignatura',
    )
    filas = Nota.objects.filter(matricula__alumno_id=alumno_id).values(
        'evaluacion',
        'valor',
        'fecha',
        alumno=Concat(
            F('matricula__alumno__apellidos'),
            Value(', '),
            F('matricula__alumno__nombre'),
            output_field=CharField(),
        ),
        asignatura=Concat(
            F('matricula__asignatura__codigo'),
            Value(' - '),
            F('matricula__asignatura__nombre'),
            output_field=CharField(),
        ),
        anio=F('matricula__anio_academico'),
    ).order_by('matricula__anio_academico', 'matricula__asignatura__nombre', 'fecha')
    dataframe = pd.DataFrame.from_records(filas)
    if dataframe.empty:
        return pd.DataFrame(columns=columnas)

    dataframe['valor'] = pd.to_numeric(dataframe['valor'])
    medias = dataframe.groupby(['asignatura', 'anio'])['valor'].transform('mean')
    dataframe['media_asignatura'] = medias
    dataframe['evaluacion'] = dataframe['evaluacion'].replace(
        dict(Nota.TipoEvaluacion.choices)
    )
    return dataframe.loc[:, columnas]


@dataclass(frozen=True)
class FilaRechazada:
    """Describe el número de fila y el motivo de rechazo."""

    fila: int
    motivo: str


@dataclass
class ResumenImportacionNotas:
    """Resume las notas importadas y las filas rechazadas."""

    importadas: int = 0
    rechazadas: list[FilaRechazada] = field(default_factory=list)

    @property
    def total_rechazadas(self):
        return len(self.rechazadas)


def _buscar_matricula(email, codigo):
    """Devuelve la matrícula única del alumno y asignatura indicados."""
    alumno_ids = list(
        Alumno.objects.filter(email__iexact=email)
        .values_list('pk', flat=True)[:2]
    )
    if not alumno_ids:
        raise ValueError('No existe un alumno con ese email.')
    if len(alumno_ids) > 1:
        raise ValueError('El email coincide con más de un alumno.')

    asignatura_ids = list(
        Asignatura.objects.filter(codigo__iexact=codigo)
        .values_list('pk', flat=True)[:2]
    )
    if not asignatura_ids:
        raise ValueError('No existe una asignatura con ese código.')
    if len(asignatura_ids) > 1:
        raise ValueError('El código coincide con más de una asignatura.')

    matriculas = list(
        Matricula.objects.filter(
            alumno_id=alumno_ids[0],
            asignatura_id=asignatura_ids[0],
        )
        .order_by('-anio_academico', 'pk')[:2]
    )
    if not matriculas:
        raise ValueError('No existe una matrícula para ese alumno y asignatura.')
    if len(matriculas) > 1:
        raise ValueError(
            'Hay varias matrículas para ese alumno y asignatura; '
            'el CSV no especifica el año académico.'
        )
    return matriculas[0]


def importar_notas_csv(archivo: IO[str] | IO[bytes]) -> ResumenImportacionNotas:
    """Valida e importa notas desde un CSV de cuatro columnas.

    La fecha de cada nota es la fecha local de importación, ya que el formato
    CSV acordado no incluye una columna de fecha.
    """
    try:
        datos = pd.read_csv(
            archivo,
            dtype=str,
            keep_default_na=False,
            skip_blank_lines=False,
        )
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise ValueError('El archivo no es un CSV válido legible.') from error

    datos.columns = [str(columna).strip() for columna in datos.columns]
    if len(set(datos.columns)) != len(datos.columns):
        raise ValueError('El CSV contiene nombres de columna duplicados.')

    faltantes = [columna for columna in COLUMNAS_REQUERIDAS if columna not in datos]
    if faltantes:
        raise ValueError(
            'Faltan columnas requeridas: ' + ', '.join(faltantes) + '.'
        )

    datos = datos.loc[:, COLUMNAS_REQUERIDAS].copy()
    for columna in COLUMNAS_REQUERIDAS:
        datos[columna] = datos[columna].map(
            lambda valor: str(valor).strip()
        )

    duplicados = datos.duplicated(
        subset=list(COLUMNAS_REQUERIDAS),
        keep='first',
    )
    resumen = ResumenImportacionNotas()

    for indice, fila in datos.iterrows():
        numero_fila = int(indice) + 2
        if duplicados.iloc[indice]:
            resumen.rechazadas.append(
                FilaRechazada(numero_fila, 'Fila duplicada en el CSV.')
            )
            continue

        vacios = [
            columna
            for columna in COLUMNAS_REQUERIDAS
            if not fila[columna]
        ]
        if vacios:
            resumen.rechazadas.append(
                FilaRechazada(
                    numero_fila,
                    'Hay valores nulos o vacíos en: ' + ', '.join(vacios) + '.',
                )
            )
            continue

        try:
            valor = Decimal(fila['valor'])
            if not valor.is_finite():
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            resumen.rechazadas.append(
                FilaRechazada(numero_fila, 'El valor no es un número válido.')
            )
            continue

        if not Decimal('0') <= valor <= Decimal('10'):
            resumen.rechazadas.append(
                FilaRechazada(
                    numero_fila,
                    'El valor debe estar entre 0 y 10.',
                )
            )
            continue

        if fila['evaluacion'] not in Nota.TipoEvaluacion.values:
            resumen.rechazadas.append(
                FilaRechazada(
                    numero_fila,
                    'La evaluación debe ser 1ª, 2ª o final.',
                )
            )
            continue

        try:
            matricula = _buscar_matricula(
                fila['email_alumno'],
                fila['codigo_asignatura'],
            )
        except ValueError as error:
            resumen.rechazadas.append(
                FilaRechazada(numero_fila, str(error))
            )
            continue

        if matricula.notas.filter(evaluacion=fila['evaluacion']).exists():
            resumen.rechazadas.append(
                FilaRechazada(
                    numero_fila,
                    'Ya existe una nota para esta evaluación y matrícula.',
                )
            )
            continue

        nota = Nota(
            matricula=matricula,
            evaluacion=fila['evaluacion'],
            valor=valor,
            fecha=timezone.localdate(),
        )
        try:
            nota.full_clean()
        except ValidationError as error:
            resumen.rechazadas.append(
                FilaRechazada(
                    numero_fila,
                    ' '.join(error.messages),
                )
            )
            continue

        nota.save()
        resumen.importadas += 1

    return resumen
