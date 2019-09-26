import datetime
from src import ModuleManager, utils
import cryptography.x509, cryptography.hazmat.backends

class Module(ModuleManager.BaseModule):
    @utils.hook("preprocess.connect")
    def preprocess_connect(self, event):
        certificate_filename = self.bot.config.get("tls-certificate", None)
        if not certificate_filename == None:
            with open(certificate_filename, "rb") as certificate_file:
                certificate = cryptography.x509.load_pem_x509_certificate(
                    certificate_file.read(),
                    cryptography.hazmat.backends.default_backend())

            today = datetime.datetime.utcnow().date()
            week = datetime.timedelta(days=7)

            not_valid_until = (today-certificate.not_valid_before.date()).days
            not_valid_after = (certificate.not_valid_after.date()-today).days

            if not_valid_until < 0:
                self.log.warn(
                    "Connecting to %s but client certificate is not valid yet",
                    [str(event["server"])])
            elif not_valid_after < 0:
                self.log.warn(
                    "Connecting to %s but client certificate is no longer "
                    "valid", [str(event["server"])])
            elif not_valid_after <= 7:
                self.log.warn(
                    "Connecting to %s but client certificate expires in a week",
                    [str(event["server"])])

