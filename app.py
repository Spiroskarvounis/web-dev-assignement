# BEGIN CODE HERE
import math
from flask import Flask, request,json, jsonify
from flask_pymongo import PyMongo
from flask_cors import CORS
from pymongo import TEXT
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
# END CODE HERE

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://127.0.0.1:27017/pspi"
CORS(app)
mongo = PyMongo(app)
mongo.db.products.create_index([("name", TEXT)])

@app.route("/search", methods=["GET"])
def search():
    # BEGIN CODE HERE
    search_term = request.args.get('name')
    pattern = '^.*' + search_term + '.*$'


    # Find all documents in the MongoDB collection that match the regular expression pattern
    results = mongo.db.products.find({'name': {'$regex': pattern}})
    results.sort("price", -1) # sort by price in descending order
    serialized_results = []
    for result in results:
        result['_id'] = str(result['_id'])
        serialized_results.append(result)

    # Serialize the results to a JSON string
    json_results = json.dumps({'products': serialized_results})
    # Return the JSON response with a status code of 200
    return json_results
    # END CODE HERE

@app.route("/add-product", methods=["POST"])
def add_product():
    # BEGIN CODE HERE
    # Get the product details from the JSON request body
    product = {
        'id': request.json['id'],
        'name': request.json['name'],
        'production_year': request.json['production_year'],
        'price': request.json['price'],
        'color': request.json['color'],
        'size': request.json['size']
    }

    exists = mongo.db.products.find_one({"name": product['name']})
    if exists is not None:
        mongo.db.products.update_one({"name": product["name"]}, {"$set": {"production_year": product["production_year"], \
            "price": product["price"], "color": product["color"], "size": product["size"]}})
        return "Updated"
    else:
        mongo.db.products.insert_one(product)
        return "Inserted new"

    # END CODE HERE

@app.route("/content-based-filtering", methods=["POST"])
def content_based_filtering():
    # BEGIN CODE HERE

    query_product = request.json

    similarities = []
    query_product = [query_product["production_year"], query_product["price"],
                    query_product["color"], query_product["size"]]
    
    # For each product in our database
    for product in mongo.db.products.find():
        if product == query_product:
            continue

        product_vector = [product["production_year"], product["price"],
                         product["color"], product["size"]]

        # Compute the cosine similarity
        dot_product = sum(query_product[i] * product_vector[i] for i in range(len(query_product)))
        magnitude_v1 = math.sqrt(sum(query_product[i] ** 2 for i in range(len(query_product))))
        magnitude_v2 = math.sqrt(sum(product_vector[i] ** 2 for i in range(len(product_vector))))
        if magnitude_v1 == 0 or magnitude_v2 == 0:
            similarity = 0
        else:
            similarity =  dot_product / (magnitude_v1 * magnitude_v2)
        if similarity > 0.7:     # end of cosine similarity computarion 
            similarities.append((product["name"], similarity))
    
    return jsonify([product[0] for product in similarities])
    # END CODE HERE



@app.route("/crawler", methods=["GET"])
def crawler():
    # BEGIN CODE HERE    
    semester = request.args.get("semester")

    if int(semester) < 1 or int(semester)> 8:
        return "Invalid semester input"

    options = webdriver.ChromeOptions()
    options.add_argument('headless') # Run Chrome in headless mode
    driver = webdriver.Chrome(options=options)
    driver.get("https://qa.auth.gr/el/x/studyguide/600000438/current")


    table = driver.find_element(By.ID, 'exam'+semester)

    rows = table.find_elements(By.TAG_NAME, 'tr')
    for row in rows:
        cols = row.find_elements(By.CLASS_NAME, 'title')
        for col in cols:
            course_titles.extend(col.text.split('\n'))

    course_titles.remove('Τίτλος')
    driver.quit()
    return jsonify({'courses': course_titles})
    # END CODE HERE