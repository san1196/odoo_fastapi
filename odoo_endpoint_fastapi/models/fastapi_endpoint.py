from odoo import _, fields, models
from ..routers import odoo_auth_endpoint


class FastapiEndpoint(models.Model):
    _inherit = "fastapi.endpoint"

    app = fields.Selection(selection_add=[("odoo_endpoint", "Odoo Endpoint")],
                           ondelete={"odoo_endpoint": "cascade"})

    def _get_fastapi_routers(self):
        if self.app == "odoo_endpoint":
            return [odoo_auth_endpoint]
        return super()._get_fastapi_routers()
