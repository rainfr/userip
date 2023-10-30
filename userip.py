import irc.bot
import irc.strings
import requests
import logging
import re  # for regular expressions

# Setting up logging
logging.basicConfig(level=logging.INFO)

class GeoIPBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667, oper_username='', oper_password=''):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel
        self.oper_username = oper_username
        self.oper_password = oper_password

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        if self.oper_username and self.oper_password:
            c.oper(self.oper_username, self.oper_password)
        c.join(self.channel)

    def on_pubmsg(self, c, e):
        args = e.arguments[0].split(" ", 2)
        cmd = args[0]

        if cmd == "!geoip":
            if len(args) < 2:
                c.privmsg(self.channel, "Usage: !geoip <nick>")
                return

            nick = args[1]
            self.get_user_ip(c, nick)

    def on_340(self, connection, event):
        user = event.source.nick
        raw_response = event.arguments[0]
        logging.info(f"Received raw response for USERIP from {user}: {raw_response}")
        parts = raw_response.split('@')
        if len(parts) == 2:
            nick = parts[0].split('=+')[0]
            ip = self.clean_ip_address(parts[1])
            if ip:
                self.run_geoip_check(connection, nick, ip)
            else:
                logging.error(f"Invalid IP format found for {nick}")
                connection.privmsg(self.channel, "Failed to parse IP information.")

    def get_user_ip(self, c, nick):
        c.send_raw(f"USERIP {nick}")

    def clean_ip_address(self, ip):
        # Use regex to extract a valid IPv4 address from the string
        match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', ip)
        return match.group(1) if match else None

    def run_geoip_check(self, c, nick, ip):
        api_key = "apikey"  # Replace with your IPstack API key
        geoip_url = f"http://api.ipstack.com/{ip}?access_key={api_key}"  # Using HTTPS
        headers = {
            "User-Agent": "GeoIPBot/1.0"  # Custom User-Agent
        }
        response = requests.get(geoip_url, headers=headers)
        data = response.json()
        if response.status_code == 200 and data.get('success', True):  # Check for success field
            city = data.get('city', 'Unknown City')
            type_ = data.get('type', 'Unknown Type')
            continent_code = data.get('continent_code', 'Unknown Continent Code')
            country_name = data.get('country_name', 'Unknown Country Name')
            country_code = data.get('country_code', 'Unknown Country Code')
            region_code = data.get('region_code', 'Unknown Region Code')
            zip_ = data.get('zip', 'Unknown ZIP')

            # Create the response message with the new fields
            response_msg = f"{nick} is located in \x0304{city}\x03. Details: Type: \x0304{type_}\x03 Continent: \x0304{continent_code}\x03 Country: \x0304{country_name}\x03,\x0304{country_code}\x03 Region: \x0304{region_code}\x03 ZIP: \x0304{zip_}\x03."
            c.privmsg(self.channel, response_msg)
        else:
            error_info = data.get('error', {}).get('info', 'Unknown error')  # Fetch the error info
            logging.error(f"Failed to fetch GeoIP data for {ip}. Error: {error_info}")  # Log the error info
            c.privmsg(self.channel, f"Failed to retrieve GeoIP information for {nick}. Error: {error_info}")

if __name__ == "__main__":
    bot = GeoIPBot("#canal", "Nickdelbot", "irc.blabla.com", 6667, "operusername", "operpass")
    bot.start()
