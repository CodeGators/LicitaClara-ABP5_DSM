# Componentes compartilhados

`licita-shared` define o contrato de armazenamento e adaptadores local e S3/R2, sem importar FastAPI, configurações ou modelos de domínio. Backend, coletor e processamento dependem deste pacote; os imports de armazenamento antigos do backend são mantidos por compatibilidade.

O cliente S3 é injetado no adaptador. Boto3 é uma dependência opcional do coletor, necessária apenas para configurar armazenamento remoto. Os testes do contrato não acessam serviços externos.
