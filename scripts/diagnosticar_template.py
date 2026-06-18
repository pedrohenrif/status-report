"""Diagnostica o acesso da service account ao template do Google Slides."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from status_report.configuracao import carregar_configuracoes
from status_report.infraestrutura.autenticacao_google import construir_servicos_google


def main() -> None:
    config = carregar_configuracoes()
    servicos = construir_servicos_google(config)
    template_id = config.id_apresentacao_modelo

    print(f"Service account: {config.email_service_account}")
    print(f"Template ID    : {template_id}")
    print()

    # Tenta buscar metadados do arquivo (requer acesso de leitura)
    print("1. Testando acesso de leitura ao template...")
    try:
        meta = (
            servicos.drive.files()
            .get(fileId=template_id, fields="id,name,mimeType,driveId,shared,permissions", supportsAllDrives=True)
            .execute()
        )
        print(f"   OK - Nome: {meta.get('name')}")
        print(f"   Tipo: {meta.get('mimeType')}")
        drive_id = meta.get("driveId")
        if drive_id:
            print(f"   ATENCAO: arquivo esta em um Shared Drive (driveId={drive_id})")
            print("   Para copiar arquivos de Shared Drives, o parametro supportsAllDrives=True e necessario.")
        else:
            print("   Arquivo esta no 'Meu Drive' (My Drive) da conta.")
    except Exception as e:
        print(f"   FALHA: {e}")
        print()
        print("   DIAGNOSTICO:")
        if "404" in str(e):
            print("   - O arquivo nao esta visivel para a service account.")
            print("   - Verifique se voce compartilhou o arquivo com:")
            print(f"     {config.email_service_account}")
            print("   - Ou se o arquivo esta em um Shared Drive com restricoes.")
        return

    print()
    print("2. Testando operacao de copia...")
    try:
        copia = (
            servicos.drive.files()
            .copy(
                fileId=template_id,
                body={"name": "TESTE_COPIA_DELETAR"},
                fields="id",
                supportsAllDrives=True,
            )
            .execute()
        )
        id_copia = copia["id"]
        print(f"   OK - Copia criada: {id_copia}")

        # Remove a copia de teste
        servicos.drive.files().delete(fileId=id_copia, supportsAllDrives=True).execute()
        print("   Copia de teste removida.")
    except Exception as e:
        print(f"   FALHA na copia: {e}")


if __name__ == "__main__":
    main()
