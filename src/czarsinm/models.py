"""
Modelos de dados para os payloads da API SINM.
Baseado nos tipos de input do sistema:
  - DadoGlebaInput (produtor, propriedade, talhao, manejos, coberturas, producoes)
  - AnaliseSoloInput / AnaliseSoloQuimicaInput / AnaliseSoloFisicaInput
  - MonitoramentoSateliteInput (sensoriamento remoto)

Contratos v1 e v2
-----------------
Os modelos serializam para os dois contratos da API. ``to_dict()`` aceita o
parâmetro ``contrato`` (``'v1'``, o padrão, ou ``'v2'``):

- **v1** — contrato congelado: aceita os nomes canônicos e os legados. Onde a
  chave canônica ainda não existe em todos os ambientes (``betaGlicosidase``,
  estreando na v6.2026 de homologação), o payload leva **as duas grafias** — é o
  payload de transição recomendado pela API, e o ambiente ignora a que não
  conhece.
- **v2** — contrato limpo (estreia em homologação em 04/08/2026): só nomes
  canônicos e ``cnpjLaboratorio`` obrigatório. Nome legado enviado ao v2 é
  descartado **em silêncio**, sem erro — por isso os modelos nunca os emitem no v2.
"""

from __future__ import annotations
import warnings
from dataclasses import dataclass, field, asdict
from typing import Optional

CONTRATOS = ("v1", "v2")
"""Contratos de payload suportados pelos modelos."""


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


def _validar_contrato(contrato: str) -> str:
    if contrato not in CONTRATOS:
        raise ValueError(
            f"Contrato '{contrato}' não reconhecido. Use um de: {', '.join(CONTRATOS)}."
        )
    return contrato


# ---------------------------------------------------------------------------
# Gleba / Talhão
# ---------------------------------------------------------------------------

@dataclass
class Produtor:
    """Dados do produtor rural."""
    cpf: str
    """CPF do produtor (somente dígitos, 11 caracteres)."""
    nome: Optional[str] = None
    """Nome completo do produtor. Opcional na API."""

    def to_dict(self) -> dict:
        return _remove_none(asdict(self))


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
    """Código da camada (6 caracteres). Usados no cálculo: '00_010', '10_020',
    '00_020', '20_040' (combinações: '00_020'+'20_040' OU '00_010'+'10_020'+'20_040').
    Qualquer código é aceito e o envio é persistido: um código fora do domínio é
    preservado mas a amostra não entra no cálculo e a API registra a inconsistência
    "Camada não prevista"; '40_060' e '60_100' são válidos porém não usados no cálculo
    e geram o aviso "Camada não utilizada na classificação". Não enviar '00_000'
    (sentinela interno; tratado como inválido)."""
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
    betaGlicosidase: Optional[float] = None
    """Beta-glicosidase em nmol/g/h (0–500). Opcional. Grafia canônica desde a
    v6.2026 — a antiga `betaGlicosidade` (erro de grafia) segue aceita no envio ao
    /api/v1, porém DEPRECIADA, e é ignorada pelo /api/v2."""
    betaGlicosidade: Optional[float] = None
    """DEPRECIADO — use `betaGlicosidase`. Mantido para não quebrar código existente:
    se informado sozinho, alimenta o campo canônico (com DeprecationWarning)."""
    densidadeSolo: Optional[float] = None
    """Densidade do solo em g/cm³ (0–3). Opcional."""
    pontos: list[Ponto] = field(default_factory=list)
    """Pontos geográficos adicionais. Opcional."""

    def __post_init__(self) -> None:
        if self.betaGlicosidade is None:
            return
        if self.betaGlicosidase is None:
            warnings.warn(
                "betaGlicosidade está depreciado (erro de grafia): use betaGlicosidase. "
                "A grafia antiga continua aceita no /api/v1 durante a transição.",
                DeprecationWarning,
                stacklevel=3,
            )
            self.betaGlicosidase = self.betaGlicosidade
        elif self.betaGlicosidade != self.betaGlicosidase:
            raise ValueError(
                "betaGlicosidase e betaGlicosidade (depreciado) foram informados com "
                f"valores diferentes ({self.betaGlicosidase} != {self.betaGlicosidade}). "
                "Informe apenas betaGlicosidase."
            )

    def to_dict(self, contrato: str = "v1") -> dict:
        _validar_contrato(contrato)
        d = _remove_none(asdict(self))
        # A grafia é reconciliada em __post_init__; a serialização decide só quais
        # chaves vão no fio. O v1 leva as duas (a produção ainda só conhece a
        # legada); o v2 aceita apenas a canônica e descartaria a legada em silêncio.
        d.pop("betaGlicosidade", None)
        d.pop("betaGlicosidase", None)
        if self.betaGlicosidase is not None:
            d["betaGlicosidase"] = self.betaGlicosidase
            if contrato == "v1":
                d["betaGlicosidade"] = self.betaGlicosidase
        return d


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
    """Código da camada (6 caracteres) da amostra física. Valores: '00_040' OU
    '00_020'+'20_040'. Qualquer código é aceito e o envio é persistido; um código fora
    do domínio é preservado como camada "Não identificado", sem rejeitar o envio.
    Não enviar '00_000' (sentinela interno)."""
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

    def to_dict(self, contrato: str = "v1") -> dict:
        _validar_contrato(contrato)
        # A amostra física não tem campo legado: o payload é idêntico nos dois contratos.
        return _remove_none(asdict(self))


# ---------------------------------------------------------------------------
# Identificação comum aos payloads de análise de solo
# ---------------------------------------------------------------------------

class _IdentificacaoAnalise:
    """Serialização dos campos de identificação comuns às análises de solo.

    Espelha o ``AnaliseSoloInputBase`` (v1) / ``AnaliseSoloV2InputBase`` (v2) da API:
    ``cpfProdutor``, ``cnpjPropriedade`` e ``cnpjLaboratorio``. A chave legada ``cnpj``
    **não** é emitida: os três ambientes (dev/hml/prd) já aceitam a canônica
    ``cnpjPropriedade``, e o v2 descartaria a legada em silêncio.
    """

    def _identificacao_dict(self, contrato: str) -> dict:
        if contrato == "v2" and not self.cnpjLaboratorio:
            raise ValueError(
                "O contrato v2 exige cnpjLaboratorio (a API responde 400 sem ele). "
                "Informe o CNPJ do laboratório ou use o contrato v1."
            )
        d: dict = {}
        if self.cpfProdutor:
            d["cpfProdutor"] = self.cpfProdutor
        if self.cnpjPropriedade:
            d["cnpjPropriedade"] = self.cnpjPropriedade
        if self.cnpjLaboratorio:
            d["cnpjLaboratorio"] = self.cnpjLaboratorio
        return d


@dataclass
class AnaliseSoloQuimica(_IdentificacaoAnalise):
    """
    Payload para cadastro de análise de solo **química** por tipo.

    Corresponde ao ``AnaliseSoloQuimicaInput`` (v1) / ``AnaliseSoloQuimicaV2Input`` (v2)
    da API: ``POST /api/{v1,v2}/analises-solo/quimica``.
    """
    amostrasQuimicas: list[AmostraQuimica]
    """Mínimo 1 amostra química obrigatória."""
    cpfProdutor: Optional[str] = None
    """CPF do produtor (obrigatório se não houver chaveClassificacaoNM)."""
    cnpjPropriedade: Optional[str] = None
    """CNPJ da propriedade (14 dígitos). Opcional."""
    cnpjLaboratorio: Optional[str] = None
    """CNPJ do laboratório (14 dígitos). Opcional no v1, **obrigatório** no v2.
    Só vincula a análise ao laboratório se ele estiver cadastrado na base — senão o
    envio é aceito com a inconsistência RN19."""

    def to_dict(self, contrato: str = "v1") -> dict:
        _validar_contrato(contrato)
        d = self._identificacao_dict(contrato)
        d["amostrasQuimicas"] = [a.to_dict(contrato) for a in self.amostrasQuimicas]
        return d


@dataclass
class AnaliseSoloFisica(_IdentificacaoAnalise):
    """
    Payload para cadastro de análise de solo **física** por tipo.

    Corresponde ao ``AnaliseSoloFisicaInput`` (v1) / ``AnaliseSoloFisicaV2Input`` (v2)
    da API: ``POST /api/{v1,v2}/analises-solo/fisica``.
    """
    amostrasFisicas: list[AmostraFisica]
    """Amostras físicas. Obrigatórias se não houver amostra física válida cadastrada
    nos últimos 10 anos."""
    cpfProdutor: Optional[str] = None
    """CPF do produtor (obrigatório se não houver chaveClassificacaoNM)."""
    cnpjPropriedade: Optional[str] = None
    """CNPJ da propriedade (14 dígitos). Opcional."""
    cnpjLaboratorio: Optional[str] = None
    """CNPJ do laboratório (14 dígitos). Opcional no v1, **obrigatório** no v2."""

    def to_dict(self, contrato: str = "v1") -> dict:
        _validar_contrato(contrato)
        d = self._identificacao_dict(contrato)
        d["amostrasFisicas"] = [a.to_dict(contrato) for a in self.amostrasFisicas]
        return d


@dataclass
class AnaliseSolo(_IdentificacaoAnalise):
    """
    Payload combinado (química + física) para cadastro de análise de solo.

    Corresponde ao ``AnaliseSoloInput`` da API — a fachada ``POST /api/v1/analises-solo``,
    que cria as **duas metades** numa transação. É **exclusiva do v1**: no v2 use
    :class:`AnaliseSoloQuimica` e :class:`AnaliseSoloFisica`, cada uma na sua rota.
    Segue mantida por compatibilidade, sem prazo de remoção.
    """
    amostrasQuimicas: list[AmostraQuimica]
    """Mínimo 1 amostra química obrigatória."""
    cpfProdutor: Optional[str] = None
    """CPF do produtor (obrigatório se não houver chaveClassificacaoNM)."""
    cnpjPropriedade: Optional[str] = None
    """CNPJ da propriedade (14 dígitos). Opcional."""
    cnpjLaboratorio: Optional[str] = None
    """CNPJ do laboratório (14 dígitos). Opcional."""
    amostrasFisicas: list[AmostraFisica] = field(default_factory=list)
    """Amostras físicas de solo. Opcional."""

    def to_dict(self, contrato: str = "v1") -> dict:
        _validar_contrato(contrato)
        if contrato == "v2":
            raise ValueError(
                "O payload combinado não existe no contrato v2. Use AnaliseSoloQuimica "
                "e AnaliseSoloFisica nas rotas /api/v2/analises-solo/{quimica,fisica}."
            )
        d: dict = {"amostrasQuimicas": [a.to_dict(contrato) for a in self.amostrasQuimicas]}
        if self.amostrasFisicas:
            d["amostrasFisicas"] = [a.to_dict(contrato) for a in self.amostrasFisicas]
        d.update(self._identificacao_dict(contrato))
        return d

    def separar(self) -> tuple[AnaliseSoloQuimica, Optional[AnaliseSoloFisica]]:
        """Divide o payload combinado nas duas metades por tipo.

        Atalho para migrar do endpoint combinado (v1) para os endpoints por tipo,
        que são os únicos no v2. A metade física é ``None`` quando não há amostras
        físicas.
        """
        quimica = AnaliseSoloQuimica(
            amostrasQuimicas=self.amostrasQuimicas,
            cpfProdutor=self.cpfProdutor,
            cnpjPropriedade=self.cnpjPropriedade,
            cnpjLaboratorio=self.cnpjLaboratorio,
        )
        fisica = None
        if self.amostrasFisicas:
            fisica = AnaliseSoloFisica(
                amostrasFisicas=self.amostrasFisicas,
                cpfProdutor=self.cpfProdutor,
                cnpjPropriedade=self.cnpjPropriedade,
                cnpjLaboratorio=self.cnpjLaboratorio,
            )
        return quimica, fisica


# ---------------------------------------------------------------------------
# Sensoriamento Remoto
# ---------------------------------------------------------------------------

@dataclass
class Indice:
    """Índice de vegetação de satélite."""
    codigoSatelite: str
    """Código do satélite. Ex: 'S01'. Valores conhecidos: 'S01'–'S09' (ver GET /api/v1/satelites).
    Um código desconhecido é aceito e o envio é persistido, mas a API registra uma inconsistência
    ("Código de satélite inválido") e marca o satélite de origem como "Não identificado".
    Não enviar 'S00' (sentinela interno; tratado como inválido)."""
    longitude: float
    """Longitude do ponto de observação."""
    latitude: float
    """Latitude do ponto de observação."""
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
    """Nome da operação. Ex: 'Revolvimento do solo'. Único valor reconhecido hoje pelo cálculo
    de nível de manejo. Uma operação não prevista é aceita (não rejeita o envio), mas gera
    inconsistência na API e é ignorada no cálculo — impacto pode ser neutro. Consulte os valores
    possíveis na documentação (tabela `operacao`)."""
    tipoOperacao: Optional[str] = None
    """Tipo da operação. Ex: 'ARAÇÃO', 'GRADAGEM', 'SUBSOLAGEM', 'ESCARIFICAÇÃO'. Opcional.
    Só é validado quando `operacao` é reconhecida; um tipo não previsto é aceito, mas gera
    inconsistência na API. Consulte os valores possíveis na documentação (tabela `tipo_operacao`)."""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SensoriamentoRemoto:
    """
    Payload para cadastro de sensoriamento remoto.

    Corresponde ao ``MonitoramentoSateliteInput`` (v1) / ``MonitoramentoSateliteV2Input``
    (v2) da API. O payload é o mesmo nos dois contratos: só a chave canônica
    ``cnpjPropriedade`` é emitida, e ela é aceita pelas duas rotas.
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
    """Código do satélite usado para declividade. Ex: 'S09'. Valores conhecidos: 'S01'–'S09'
    (ver GET /api/v1/satelites). Código desconhecido é aceito, mas gera inconsistência na API
    (vide `Indice.codigoSatelite`). Não enviar 'S00'."""
    indices: list[Indice]
    """Mínimo 1 índice obrigatório."""
    cpfProdutor: Optional[str] = None
    """CPF do produtor (obrigatório se não houver chaveClassificacaoNM)."""
    cnpjPropriedade: Optional[str] = None
    """CNPJ da propriedade (14 dígitos). Opcional."""
    cnpjEmpresaSensoriamento: Optional[str] = None
    """CNPJ da empresa responsável pelo sensoriamento remoto (14 dígitos). Opcional."""
    codigoSatelitePlantioContorno: Optional[str] = None
    """Código do satélite para plantio em contorno. Ex: 'S08'."""
    codigoSateliteTerraceamento: Optional[str] = None
    """Código do satélite para terraceamento. Ex: 'S07'."""
    interpretacoesCoberturaSolo: list[InterpretacaoCoberturaSolo] = field(default_factory=list)
    interpretacoesCultura: list[InterpretacaoCultura] = field(default_factory=list)
    interpretacoesManejo: list[InterpretacaoManejo] = field(default_factory=list)

    def to_dict(self, contrato: str = "v1") -> dict:
        _validar_contrato(contrato)
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
        if self.cnpjPropriedade:
            d["cnpjPropriedade"] = self.cnpjPropriedade
        if self.cnpjEmpresaSensoriamento:
            d["cnpjEmpresaSensoriamento"] = self.cnpjEmpresaSensoriamento
        if self.codigoSatelitePlantioContorno:
            d["codigoSatelitePlantioContorno"] = self.codigoSatelitePlantioContorno
        if self.codigoSateliteTerraceamento:
            d["codigoSateliteTerraceamento"] = self.codigoSateliteTerraceamento
        return d
