# NOTE: Replace environment variables (BotToken, chat_id) with your own values
# Make sure not to hardcode tokens in your script for security reasons.

import json
import boto3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import os
import requests
import pandas as pd
import datetime

date = datetime.datetime.now()  # setting up the date and time
bot = os.environ['BotToken']  # this is bot token
chat = os.environ['chat_id']  # recipient's chat ID
all_product_data = []

categories = {
    "Baby_Products": "baby",
    "Beauty": "beauty",
    "Car_and_Bike": "automotive",
    "Electronics": "electronics",
    "Computers_&_Accessories": "computers",
    "Home_&_Kitchen": "kitchen",
    "Sports_Fitness_Outdoors": "sports",
    "Toys_Games": "toys",
    "Watches": "watches",
    "Bags_Wallets_Luggage": "luggage"
}


def get_driver():
    options = Options()
    options.binary_location = '/opt/headless-chromium'
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--single-process')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome('/opt/chromedriver', chrome_options=options)
    driver.implicitly_wait(2)
    return driver


def get_products(driver, category):
    URL = f"https://www.amazon.in/gp/bestsellers/{category}/"
    driver.get(URL)
    products_locator = "gridItemRoot"
    total_products = driver.find_elements(By.ID, products_locator)
    return total_products


def parse_products(product, category_name):
    # getting the Rank of the product
    try:
        rank_tag = product.find_element(By.CLASS_NAME, "zg-bdg-text")
        rank = rank_tag.text
    except:
        rank = "No Rank Present"

    # getting the ASIN of the product
    ASIN_Tag = product.find_element(By.XPATH, '*//div[@data-asin]')
    ASIN = ASIN_Tag.get_attribute("data-asin")

    # getting the Name of the product
    try:
        name_tag = product.find_element(By.XPATH, f"//*[@id='{ASIN}']/div/div/a/span")
        product_name = name_tag.text
    except:
        product_name = "No Product Name Present"

    # getting the Price of the product
    try:
        price_tag = product.find_element(By.XPATH, f"//*[@id='{ASIN}']//span[@class='a-size-base a-color-price']/span")
        price = price_tag.text
    except:
        price = "No Price Available"

    # getting the Stars of the product
    try:
        stars_tag = product.find_element(By.XPATH, f"//*[@id='{ASIN}']//i/parent::a")
        stars = stars_tag.get_attribute("title")
    except:
        stars = "No Stars"

    # getting the Total Ratings of the product
    try:
        ratings_tag = product.find_element(By.XPATH, f"//*[@id='{ASIN}']//i/following-sibling::span")
        ratings = ratings_tag.text
    except:
        ratings = "No Rating Present"

    # getting the Image of the product
    try:
        image_tag = product.find_element(By.XPATH, f"//*[@id='{ASIN}']/a[1]/div/img")
        image = image_tag.get_attribute("src")
    except:
        image = "No Image Present"

    # url of the product
    product_url = f"https://www.amazon.in/s?k={ASIN}"

    return {
        "Date": f"{date.strftime('%d-%b-%Y')}",
        "Category": category_name,
        "Rank": rank,
        "ASIN": ASIN,
        "Name": product_name,
        "Price": price,
        "Stars": stars,
        "Ratings": ratings,
        "Product URL": product_url,
        "Image": image
    }


def telegram_sms(filename):
    # SENDING DATA TO TELEGRAM BOT

    # path to the file to be sent
    file_path = filename

    url = f'https://api.telegram.org/bot{bot}/sendDocument'
    files = {'document': open(file_path, 'rb')}
    params = {'chat_id': chat}
    response = requests.post(url, files=files, params=params)
    if response.status_code == 200:
        print('File sent successfully!')
    else:
        print(f'Error sending file. Status code: {response.status_code}, Response: {response.text}')


# def save_to_s3_bucket(filename):

#   file_to_upload = os.path.basename(filename)
#  object_key = 'NewFunction'

# save to s3 bucket
# s3_client.upload_file(filename, bucketName, f'{object_key}/{file_to_upload}')
# print("File uploaded to S3 ")

def lambda_handler(event, context):
    # initiating the WebDriver
    driver = get_driver()

    # running a loop to iterate over each defined category
    for category_name, category_path in categories.items():
        # getting the products from the category
        products = get_products(driver, category_path)

        # parsing data from each products collected
        product_data = [parse_products(product, category_name) for product in products[:len(products)]]

        # extending the list with the product data for the current category
        all_product_data.extend(product_data)

    # create a DataFrame from the accumulated product data
    all_products_df = pd.DataFrame(all_product_data)

    # setting a varibale to define a custom name for each day
    filename = f'/tmp/{date.strftime("%d-%b-%Y")}-Main_Bestseller.csv'

    # converting the DataFrame into a CSV file to process it further
    all_products_df.to_csv(filename, index=None, encoding='utf-8-sig')

    # sending file to telegram
    telegram_sms(filename)

    # uploading file to S3
    # save_to_s3_bucket(filename)

    # closing and quiting the WebDriver and
    driver.close()
    driver.quit()

    response = {
        "statusCode": 200,
        "body": "Files are sent to telegram"
    }

    return response
