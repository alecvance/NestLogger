#use python 3
import http.client
from urllib.parse import urlparse
import json
import time
from datetime import datetime
import configparser
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def email_alert(subjectText, messageText):

    msg = MIMEMultipart()
    msg['From']=email
    msg['To']=email
    msg['Subject']="Nestlogger alert: "+ subjectText

    # add in the message body
    msg.attach(MIMEText(messageText, 'plain'))

    # connect a server, login and send the mail
   # s = smtplib.SMTP(host=smtp, port=smtp_port)
    s = smtplib.SMTP_SSL("" + smtp + ":" + smtp_port)

    #s.starttls()
    s.login(email,password)
    s.sendmail(email,email,msg.as_string())
    s.quit()
    del msg
    return


start_time = time.perf_counter()

#read the config file
config = configparser.ConfigParser()
config.read("nest.config")

# your nest api token
token = config['DEFAULT']['token']

#email to send alerts to
email = config['DEFAULT']['email']

#password for email
password = config['DEFAULT']['password']

#smtp (sendmail) configuration
smtp = config['DEFAULT']['smtp']
smtp_port = config['DEFAULT']['smtp_port']

# maximum relative humidity; greater than this will trigger an email if email is set.
default_max_rh = int(config['DEFAULT']['max_rh'])

#connect to the Nest API to get current status of each thermostat in account
conn = http.client.HTTPSConnection("developer-api.nest.com")
headers = {'authorization': "Bearer {0}".format(token)}
conn.request("GET", "/", headers=headers)
response = conn.getresponse()

if response.status == 307:
    redirectLocation = urlparse(response.getheader("location"))
    conn = http.client.HTTPSConnection(redirectLocation.netloc)
    conn.request("GET", "/", headers=headers)
    response = conn.getresponse()
    if response.status != 200:
        raise Exception("Redirect with non 200 response")

data = response.read()
#print(data.decode("utf-8"))
parsed_json = json.loads(data)

devices = parsed_json['devices']
thermostats = devices['thermostats']

for deviceID, thermostat in thermostats.items():

    device_name_long = thermostat['name_long']
    filename = device_name_long + ".log"

    max_rh = default_max_rh
    if config.has_option(device_name_long,'max_rh'):
	    max_rh = int(config[device_name_long]['max_rh']) 
	    #print("max_rh for " + device_name_long + " is " + format(max_rh))

	    
    if max_rh == 0:
    	print("config error: max_rh not defined / too low for ".device_name_long)
    	max_rh = default_max_rh


    

    print (device_name_long +":")

    #print(deviceID, 'corresponds to', device_name_long)
    #for thermostatDataKey, thermostatData in thermostat.items():
        #print(device_name_long, " ", thermostatDataKey, ': ', thermostatData)

    humidity = thermostat['humidity']
    hvac_state = thermostat['hvac_state']
    hvac_mode = thermostat['hvac_mode']
    target_temperature_f = thermostat['target_temperature_f']
    ambient_temperature_f = thermostat['ambient_temperature_f']
    fan_timer_active = thermostat['fan_timer_active']

    timeStr = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with open(filename, "a") as f:
        f.write('{}\t{}\t{}\t{}\t{}\t{}\r'.format(timeStr,ambient_temperature_f,humidity,hvac_state,target_temperature_f,fan_timer_active))

    messageText = "\n\r  Status: \t{}F \t{}%RH \tState: {} \n\r  Target: \t" .format(ambient_temperature_f,humidity, hvac_state)

    if(hvac_mode == "heat-cool"):
        target_temperature_f = thermostat['target_temperature_high_f']
        #target temp is a range
        messageText += "{}F-{}F".format(thermostat['target_temperature_low_f'],target_temperature_f)
    else:
        messageText += "{}F".format(target_temperature_f)

    messageText +=  " \t{}%RH \n\r".format(max_rh)

    if (hvac_state == "off"):
	    if (int(humidity) > max_rh):

	        messageText += ("# WARNING: Humidity at {} is above {}%RH. \n\r").format(device_name_long,max_rh)

	        if(email):
	            email_alert(device_name_long, messageText)
	            print("sent email.")

	    else:
	         messageText += "Humidity at {} is within range. ( <= {}%RH.) \n\r".format(device_name_long,max_rh)

    print(messageText)

print("run time:", time.perf_counter() - start_time, "sec")
