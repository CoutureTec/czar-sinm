"""
Modelos de dados para os payloads da API SINM.
Baseado nos tipos de input do sistema:
  - DadoGlebaInput (produtor, propriedade, talhao, manejos, coberturas, producoes)
  - AnaliseSoloInput (cpfProdutor, cnpj, amostras)
  - MonitoramentoSateliteInput (sensoriamento remoto)
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _remove_none(d: dict) -> dict:
    """Remove recursivamente chaves com valor None."""
    result = {}
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, dict):
            result[k] = _remove_none(v)
        elif isinstance(v, list):
            result[k] = [_remove_none(i) if isinstance(i, dict) else i for i in v]
        else:
            result[k] = v
    return result


# ---------------------------------------------------------------------------
# Gleba / Talhão
# ---------------------------------------------------------------------------

@dataclass
class Produtor:
    """Dados do produtor rural."""
    nome: str
    """Nome completo do produtor."""
    cpf: str
    """CPF do produtor (somente dígitos, 11 caracteres)."""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Propriedade:
    """Dados da propriedade rural."""
    nome: str
    """Nome da fazenda/propriedade."""
    codigoCar: str
    """Código CAR (43 caracteres). Ex: 'MT-5107248-1025F299474640148FE845C7A0B62635'"""
    codigoIbge: str
    """Código IBGE do município. Ex: '3509502'"""
    poligono: str
    """Polígono WKT da propriedade. Ex: 'POLYGON ((-58.91 -13.50, ...))'"""
    cnpj: Optional[str] = None
    """CNPJ da empresa (somente dígitos, 14 caracteres). Opcional."""

    def to_dict(self) -> dict:
        return _remove_none(asdict(self))


@dataclass
class Talhao:
    """Dados do talhão."""
    poligono: str
    """Polígono WKT do talhão. Ex: 'POLYGON ((-47.11 -22.81, ...))'"""
    area: float
    """Área em hectares."""
    tipoProdutor: str
    """Tipo de produtor: 'Proprietário' ou 'Arrendatário'."""
    plantioContorno: int
    """Plantio em contorno: 0 (não) ou 1 (sim)."""
    cnpjOperador: Optional[str] = None
    """CNPJ da empresa operadora (client ID no Keycloak). Opcional."""

    def to_dict(self) -> dict:
        return _remove_none(asdict(self))


@dataclass
class Operacao:
    nomeOperacao: str
    """Nome da operação de manejo. Ex: 'Revolvimento do solo'."""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TipoOperacao:
    tipo: str
    """Tipo de operação. Ex: 'ARAÇÃO', 'GRADAGEM', 'PLANTIO_DIRETO'."""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Manejo:
    """Registro de operação de manejo do solo."""
    data: str
    """Data da operação (formato 'YYYY-MM-DD')."""
    operacao: Operacao
    tipoOperacao: TipoOperacao

    def to_dict(self) -> dict:
        return {
            "data": self.data,
            "operacao": self.operacao.to_dict(),
            "tipoOperacao": self.tipoOperacao.to_dict(),
        }


@dataclass
class CoberturaSolo:
    """Avaliação de cobertura do solo (palhada)."""
    dataAvaliacao: str
    """Data da avaliação (formato 'YYYY-MM-DD')."""
    porcentualPalhada: int
    """Percentual de palhada (0–100), valor inteiro."""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Cultura:
    codigo: str
    """Código da cultura. Ex: '001' (soja), '018' (milho), '020' (sorgo), '072' (trigo)."""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Producao:
    """Registro de produção (safra realizada ou prevista)."""
    cultura: Cultura
    ilp: bool = False
    """Integração Lavoura-Pecuária. Obrigatório (padrão False)."""
    dataPlantio: Optional[str] = None
    """Data de plantio realizado (formato 'YYYY-MM-DD')."""
    dataColheita: Optional[str] = None
    """Data de colheita realizada (formato 'YYYY-MM-DD')."""
    dataPrevisaoPlantio: Optional[str] = None
    """Data prevista de plantio (formato 'YYYY-MM-DD'). Para safra futura."""
    dataPrevisaoColheita: Optional[str] = None
    """Data prevista de colheita (formato 'YYYY-MM-DD'). Para safra futura."""

    def to_dict(self) -> dict:
        d: dict = {
            "cultura": self.cultura.to_dict(),
            "ilp": self.ilp,
        }
        if self.dataPlantio:
            d["dataPlantio"] = self.dataPlantio
        if self.dataColheita:
            d["dataColheita"] = self.dataColheita
        if self.dataPrevisaoPlantio:
            d["dataPrevisaoPlantio"] = self.dataPrevisaoPlantio
        if self.dataPrevisaoColheita:
            d["dataPrevisaoColheita"] = self.dataPrevisaoColheita
        return d


@dataclass
class DadoGleba:
    """
    Payload completo para cadastro de talhão/gleba.

    Corresponde ao DadoGlebaInput da API.
    """
    produtor: Produtor
    propriedade: Propriedade
    talhao: Talhao
    manejos: list[Manejo]
    """Mínimo 1 operação de manejo obrigatória."""
    coberturas: list[CoberturaSolo]
    """Mínimo 1 avaliação de cobertura obrigatória."""
    producoes: list[Producao]
    """Mínimo 1 produção (passada ou futura) obrigatória."""

    def to_dict(self) -> dict:
        return {
            "produtor": self.produtor.to_dict(),
            "propriedade": self.propriedade.to_dict(),
            "talhao": self.talhao.to_dict(),
            "manejos": [m.to_dict() for m in self.manejos],
            "coberturas": [c.to_dict() for c in self.coberturas],
            "producoes": [p.to_dict() for p in self.producoes],
        }


# ---------------------------------------------------------------------------
# Operação (fluxo combinado)
# ---------------------------------------------------------------------------

@dataclass
class DadosInput:
    """
    Payload para o endpoint POST /api/v1/operacoes.

    Referencia recursos já cadastrados pelos seus UUIDs e fornece as
    produções para disparar o processamento da classificação de NM.
    """
    uuidGleba: str
    """UUID da gleba previamente cadastrada."""
    uuidAnaliseSolo: str
    """UUID da análise de solo previamente cadastrada."""
    uuidSensoriamentoRemoto: str
    """UUID do sensoriamento remoto previamente cadastrado."""
    producaoAtual: Producao
    """Produção da safra atual."""
    producoesAnteriores: list

    def to_dict(self) -> dict:
        return {
            "uuidGleba": self.uuidGleba,
            "uuidAnaliseSolo": self.uuidAnaliseSolo,
            "uuidSensoriamentoRemoto": self.uuidSensoriamentoRemoto,
            "producaoAtual": self.producaoAtual.to_dict(),
            "producoesAnteriores": [p.to_dict() for p in self.producoesAnteriores],
        }


# ---------------------------------------------------------------------------
# Análise de Solo
# ---------------------------------------------------------------------------

@dataclass
class Ponto:
    """Ponto geográfico adicional associado a uma amostra."""
    longitude: float
    latitude: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AmostraQuimica:
    """Amostra química de solo coletada (AmostraQuimicaInput)."""
    cpfResponsavelColeta: str
    """CPF do responsável pela coleta (somente dígitos)."""
    dataColeta: str
    """Data da coleta (formato 'YYYY-MM-DD')."""
    longitude: float
    """Longitude do ponto de coleta."""
    latitude: float
    """Latitude do ponto de coleta."""
    camada: str
    """Camada de coleta (6 caracteres). Valores aceitos: '00_010', '10_020',
    '00_020', '20_040', '00_040', '40_060', '60_100'."""
    calcio: float
    """Cálcio em cmolc/dm³ (0–50)."""
    magnesio: float
    """Magnésio em cmolc/dm³ (0–30)."""
    potassio: float
    """Potássio em mg/dm³ (0–1000)."""
    aluminio: float
    """Alumínio em cmolc/dm³ (0–100)."""
    acidezPotencial: float
    """Acidez potencial H+Al em cmolc/dm³ (0–100)."""
    enxofre: float
    """Enxofre em mg/dm³ (0–100)."""
    mos: float
    """Matéria orgânica do solo em g/kg (0–300)."""
    sodio: Optional[float] = None
    """Sódio em mg/dm³ (0–1000). Opcional."""
    phh2o: Optional[float] = None
    """pH em água (0–14). Opcional."""
    phcacl2: Optional[float] = None
    """pH em CaCl2 (0–14). Opcional."""
    fosforoMehlich: Optional[float] = None
    """Fósforo Mehlich em mg/dm³ (0–100). Opcional."""
    fosforoResina: Optional[float] = None
    """Fósforo Resina em mg/dm³ (0–100). Opcional."""
    arilsulfatase: Optional[float] = None
    """Arilsulfatase em nmol/g/h (0–800). Opcional."""
    betaGlicosidade: Optional[float] = None
    """Beta-glicosidade em nmol/g/h (0–500). Opcional."""
    densidadeSolo: Optional[float] = None
    """Densidade do solo em g/cm³ (0–3). Opcional."""
    pontos: list[Ponto] = field(default_factory=list)
    """Pontos geográficos adicionais. Opcional."""

    def to_dict(self) -> dict:
        return _remove_none(asdict(self))


# Alias para compatibilidade com código existente
Amostra = AmostraQuimica


@dataclass
class AmostraFisica:
    """Amostra física de solo coletada (AmostraFisicaInput)."""
    dataColeta: str
    """Data da coleta (formato 'YYYY-MM-DD')."""
    longitude: float
    """Longitude do ponto de coleta."""
    latitude: float
    """Latitude do ponto de coleta."""
    camada: str
    """Camada de coleta (6 caracteres). Valores aceitos: '00_010', '10_020',
    '00_020', '20_040', '00_040', '40_060', '60_100'."""
    areia: float
    """Areia em g/kg (0–100)."""
    silte: float
    """Silte em g/kg (0–100)."""
    argila: float
    """Argila em g/kg (0–100)."""
    cpfResponsavelColeta: Optional[str] = None
    """CPF do responsável pela coleta (somente dígitos). Opcional."""
    pontos: list[Ponto] = field(default_factory=list)
    """Pontos geográficos adicionais. Opcional."""

    def to_dict(self) -> dict:
        return _remove_none(asdict(self))


@dataclass
class AnaliseSolo:
    """
    Payload para cadastro de análise de solo.

    Corresponde ao AnaliseSoloInput da API.
    """
    amostrasQuimicas: list[AmostraQuimica]
    """Mínimo 1 amostra química obrigatória."""
    cpfProdutor: Optional[str] = None
    """CPF do produtor (obrigatório se não houver chaveClassificacaoNM)."""
    cnpj: Optional[str] = None
    """CNPJ da empresa (opcional)."""
    cnpjLaboratorio: Optional[str] = None
    """CNPJ do laboratório (14 dígitos). Opcional."""
    amostrasFisicas: list[AmostraFisica] = field(default_factory=list)
    """Amostras físicas de solo. Opcional."""

    def to_dict(self) -> dict:
        d: dict = {"amostrasQuimicas": [a.to_dict() for a in self.amostrasQuimicas]}
        if self.amostrasFisicas:
            d["amostrasFisicas"] = [a.to_dict() for a in self.amostrasFisicas]
        if self.cpfProdutor:
            d["cpfProdutor"] = self.cpfProdutor
        if self.cnpj:
            d["cnpj"] = self.cnpj
        if self.cnpjLaboratorio:
            d["cnpjLaboratorio"] = self.cnpjLaboratorio
        return d


# ---------------------------------------------------------------------------
# Sensoriamento Remoto
# ---------------------------------------------------------------------------

@dataclass
class Indice:
    """Índice de vegetação de satélite."""
    codigoSatelite: str
    """Código do satélite. Ex: 'S01'."""
    coordenada: str
    """Coordenada WKT do ponto. Ex: 'POINT (-47.108493 -22.811532)'"""
    data: str
    """Data da observação (formato 'YYYY-MM-DD')."""
    ndvi: float
    """Índice NDVI."""
    ndti: float
    """Índice NDTI."""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class InterpretacaoCoberturaSolo:
    """Interpretação de cobertura do solo via satélite."""
    dataAvaliacao: str
    """Data da avaliação (formato 'YYYY-MM-DD')."""
    porcentualPalhada: int
    """Percentual de palhada (0–100), valor inteiro."""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class InterpretacaoCultura:
    """Interpretação de cultura via satélite."""
    tipoCultivo: str
    """Tipo de cultivo. Ex: 'Cultivo de 2ª safra'."""
    dataInicio: str
    """Data de início (formato 'YYYY-MM-DD')."""
    dataFim: str
    """Data de fim (formato 'YYYY-MM-DD')."""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class InterpretacaoManejo:
    """Interpretação de manejo via satélite."""
    data: str
    """Data da operação (formato 'YYYY-MM-DD')."""
    operacao: str
    """Nome da operação. Ex: 'Revolvimento do solo'."""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SensoriamentoRemoto:
    """
    Payload para cadastro de sensoriamento remoto.

    Corresponde ao MonitoramentoSateliteInput da API.
    """
    dataInicial: str
    """Data inicial do período monitorado (formato 'YYYY-MM-DD')."""
    dataFinal: str
    """Data final do período monitorado (formato 'YYYY-MM-DD')."""
    declividadeMedia: int
    """Declividade média do talhão (0–100), valor inteiro."""
    plantioContorno: int
    """Plantio em contorno detectado: 0 ou 1."""
    terraceamento: int
    """Terraceamento detectado: 0 ou 1."""
    codigoSateliteDeclividadeMedia: str
    """Código do satélite usado para declividade. Ex: 'S09'."""
    indices: list[Indice]
    """Mínimo 1 índice obrigatório."""
    cpfProdutor: Optional[str] = None
    """CPF do produtor (obrigatório se não houver chaveClassificacaoNM)."""
    cnpj: Optional[str] = None
    """CNPJ da empresa (opcional)."""
    codigoSatelitePlantioContorno: Optional[str] = None
    """Código do satélite para plantio em contorno. Ex: 'S08'."""
    codigoSateliteTerraceamento: Optional[str] = None
    """Código do satélite para terraceamento. Ex: 'S07'."""
    interpretacoesCoberturaSolo: list[InterpretacaoCoberturaSolo] = field(default_factory=list)
    interpretacoesCultura: list[InterpretacaoCultura] = field(default_factory=list)
    interpretacoesManejo: list[InterpretacaoManejo] = field(default_factory=list)

    def to_dict(self) -> dict:
        d: dict = {
            "dataInicial": self.dataInicial,
            "dataFinal": self.dataFinal,
            "declividadeMedia": self.declividadeMedia,
            "plantioContorno": self.plantioContorno,
            "terraceamento": self.terraceamento,
            "codigoSateliteDeclividadeMedia": self.codigoSateliteDeclividadeMedia,
            "indices": [i.to_dict() for i in self.indices],
            "interpretacoesCoberturaSolo": [c.to_dict() for c in self.interpretacoesCoberturaSolo],
            "interpretacoesCultura": [c.to_dict() for c in self.interpretacoesCultura],
            "interpretacoesManejo": [m.to_dict() for m in self.interpretacoesManejo],
        }
        if self.cpfProdutor:
            d["cpfProdutor"] = self.cpfProdutor
        if self.cnpj:
            d["cnpj"] = self.cnpj
        if self.codigoSatelitePlantioContorno:
            d["codigoSatelitePlantioContorno"] = self.codigoSatelitePlantioContorno
        if self.codigoSateliteTerraceamento:
            d["codigoSateliteTerraceamento"] = self.codigoSateliteTerraceamento
        return d
