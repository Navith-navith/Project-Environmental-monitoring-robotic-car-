from flask import Flask, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

app = Flask(__name__)

# Set up Google Sheets credentials
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
try:
    creds = ServiceAccountCredentials.from_json_keyfile_name(r"C:\Users\Akshay\OneDrive\Desktop\EEX\april 25 pico\credentials_key.json", scope)
    client = gspread.authorize(creds)
    sheet_url = 'https://docs.google.com/spreadsheets/d/13Z7qMtifDp27RAb1RSCFWLNBIB86y4IL3yFXuBayT-4/edit#gid=0'
    sheet = client.open_by_url(sheet_url).sheet1
except Exception as e:
    print("Error initializing Google Sheets client:", e)

@app.route('/upload', methods=['POST'])
def upload_data():
    try:
        data = request.json
        dust_sensor = data.get('dust_sensor')
        mq135_CO2_data = data.get('mq135_CO2_data')
        mq135_CO_data = data.get('mq135_CO_data')
        mq135_NH4_data = data.get('mq135_NH3_data')
        mq6_benzene_data = data.get('mq6_benzene_data')
        ldr_data=data.get('ldr_data')
        noise_data = data.get('noise_data')
        dht11_temp_data = data.get('dht_temp_data')
        dht11_humidity_data = data.get('dht_humidity_data')
        
        gps_latitude=data.get('gps_latitude')
        gps_longitude=data.get('gps_longitude')
        
        timestamp = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        data_with_timestamp = [timestamp, dust_sensor, mq135_CO2_data, mq135_CO_data, mq135_NH4_data , mq6_benzene_data , noise_data,dht11_temp_data,dht11_humidity_data,ldr_data,gps_longitude,gps_latitude]
        
        sheet.append_row(data_with_timestamp)
        return 'Data uploaded successfully'
    except Exception as e:
        return f"Error uploading data to Google Sheets: {e}"

if __name__ == '__main__':
    app.run(host='0.0.0.0')
