"""Build the public Nacos example archive; never reads local ai-secrets.yml."""
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
CLOUD = HERE.parent
with zipfile.ZipFile(HERE / 'nacos-config-import.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in ['common-config.yaml', 'gateway.yaml', 'user-service.yaml',
                 'ticket-service.yaml', 'consultation-service.yaml']:
        archive.write(HERE / name, f'DEFAULT_GROUP/{name}')
    for service in ['gateway', 'user-service', 'ticket-service', 'consultation-service']:
        for profile in ['dev', 'prod']:
            archive.write(CLOUD / service / f'src/main/resources/application-{profile}.yml',
                          f'DEFAULT_GROUP/{service}-{profile}.yaml')
print('Built 13 public configuration examples; secrets stay in environment/local files.')
