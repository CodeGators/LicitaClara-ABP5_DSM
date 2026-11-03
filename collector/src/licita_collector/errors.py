class CollectionError(Exception):
    code = "ERRO_COLETA"


class Unavailable(CollectionError):
    code = "ARQUIVO_INDISPONIVEL"


class TransientFailure(CollectionError):
    code = "FALHA_REDE"


class InvalidArchive(CollectionError):
    code = "ARQUIVO_INVALIDO"


class Busy(CollectionError):
    code = "COLETA_EM_EXECUCAO"
