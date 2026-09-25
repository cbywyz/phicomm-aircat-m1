"""Config flow for phicomm_aircat (no user input required)."""

from homeassistant import config_entries

from .const import DOMAIN


class AirCatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="斐讯悟空 M1 空气检测器", data={})
        return self.async_show_form(step_id="user")
