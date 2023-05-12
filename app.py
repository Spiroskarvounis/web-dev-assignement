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
    # Δεχόμαστε την παράμετρο και φτιάχνουμε ένα pattern διότι θέλουμε να δούμε αν ανήκει στο όνομα κάποιου
    # προιόντος
    search_term = request.args.get('name')
    pattern = '^.*' + search_term + '.*$'

    # Αν είναι κενό το πεδίο αναζήτησης τότε να μην εμφανίζει τίποτα (διαφορετικά εμφανίζει όλη τη βάση)
    if search_term == "":
        return "error"

    # search στη βάση
    results = mongo.db.products.find({'name': {'$regex': pattern}})
    results.sort("price", -1) # sort με βάση την τιμή σε φθίνουσα 
    serialized_results = []
    # Κάνουμε το default id που δίνει η mongo cast σε str
    for result in results:
        result['_id'] = str(result['_id'])
        serialized_results.append(result)

    serialized_result = json.dumps(serialized_results)
    return (serialized_result)
    # END CODE HERE

@app.route("/add-product", methods=["POST"])
def add_product():
    # BEGIN CODE HERE

    # Αντιστοιχούμε τις τιμές από τα forms σε ένα dictionairy. Γίνονται έλεγχοι τιμών για
    # production_year, price, color, size. Για λάθος τύπο δεδομένων θα εμφανίζεται το μήνυμα του except
    try:
        product = {
            'name': request.json['name'],
            'production_year': int(request.json['production_year']),
            'price': float(request.json['price']),
            'color': int(request.json['color']),
            'size': int(request.json['size'])
        }
    except (KeyError, ValueError):
        return "Production Year, Price, Color, Size must be numeric values" 

    # Αν κάποια από τις τιμές που δόθηκαν είναι κενή τότε επιστρέφει ανάλογο μήνυμα
    i = 0
    for prod in product.values():
        if prod == "":
            return "Συμπλήρωσε τα όπως πρέπει"

    
    # Search στη βάση ώστε να διαπιστωθεί αν υπάρχει προιόν με ακριβώς το ίδιο όνομα.
    # Αν ναι κάνει update όλες τις τιμές πέραν του ονόματος και φυσικά του _id
    exists = mongo.db.products.find_one({"name": product['name']})
    if exists is not None:
        mongo.db.products.update_one({"name": product["name"]}, {"$set": {"production_year": product["production_year"], \
            "price": product["price"], "color": product["color"], "size": product["size"]}})
        return "Updated"
    else:
        # Αν δεν υπάρχει ήδη στη βάση προιόν με το ίδιο όνομα τότε το προσθέτουμε
        mongo.db.products.insert_one(product)
        return "Inserted new"

    # END CODE HERE

@app.route("/content-based-filtering", methods=["POST"])
def content_based_filtering():
    # BEGIN CODE HERE

    # request json αρχείο με το προιόν που θα αναζητηθεί
    query_product = request.json

    # Καθαρίζουμε τις περιττές τιμές όπως το όνομα και το id 
    # και κρατάμε μόνο αυτές που μας ενδιαφέρουν
    similarities = []
    query_product = [query_product["production_year"], query_product["price"],
                    query_product["color"], query_product["size"]]
    
    # Για κάθε προιόν της βάσης:
    for product in mongo.db.products.find():
        if product == query_product: # Αν το προιόν είναι το ίδιο με του input δε κάνει τίποτα.
            continue
        
        product_vector = [product["production_year"], product["price"],
                         product["color"], product["size"]]

        # Εδώ υπολογίζουμε την ομοιότητα συνημιτόνου σύμφωνα με τις διαφάνειες
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
    # Μεταβλητή που φιλοξενεί την τιμή της παραμέτρου.
    semester = request.args.get("semester")
    course_titles = []
    
    # Έλεγχος ώστε τα εξάμηνα να είναι από 1-8 που διατίθενται στο url που μας δίνεται
    if int(semester) < 1 or int(semester)> 8:
        return "Invalid semester input"

    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    driver = webdriver.Chrome(options=options)
    driver.get("https://qa.auth.gr/el/x/studyguide/600000438/current")


    # Ψάχνουμε τον πίνακα με id= 'exam'+semester, διότι με inspect στην html παρατηρούμε ότι 
    # όλοι οι πίνακες με τα courses έχουν id τη λέξη exam με κολλημένο το εξάμηνο 
    table = driver.find_element(By.ID, 'exam'+semester)

    # Βρίσκουμε τις γραμμές του παραπάνω πίνακα
    rows = table.find_elements(By.TAG_NAME, 'tr')
    for row in rows:
        # Ψάχνουμε τις στήλες με class_name= 'title', που διαπιστώσαμε πάλι με inspect στην html
        cols = row.find_elements(By.CLASS_NAME, 'title')
        for col in cols:
            # προσθέτουμε την τιμή της στήλης στο αποτέλεσμα
            course_titles.extend(col.text.split('\n'))

    # Αφαιρούμε την τιμή 'Τίτλος' που προστίθεται αυτόματα, γιατί είναι της κλάσης 'title'
    course_titles.remove('Τίτλος')
    driver.quit()
    return jsonify({'courses': course_titles})
    # END CODE HERE