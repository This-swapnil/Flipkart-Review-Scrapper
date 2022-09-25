from crypt import methods
from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup as bs
from urllib.request import urlopen as uReq
import pymongo


app = Flask(__name__)  # Initializing the flask app with the name "app"


# base url
@app.route("/", methods=['POST', 'GET'])
def index():
    if request.methods == "POST":
        # Obtaining the search string entered in the form
        searchString = request.form['content'].replace(" ", "")
        try:
            dbConn = pymongo.MongoClient(
                "mongodb://localhost:27017/")  # connecting to mongoDB
            # connecting the database called crawlerDB if not present it will create
            db = dbConn['crawlerDB']
            # searching the collection with the name same as the keyword
            if searchString in db.list_collection_names():
                review = []
                for reviews in db[searchString].find({}, {"_id": 0}):
                    review.append(reviews)
                return render_template("results.html", reviews=list(review))
            else:
                # preparing the URL to search the product on flipkart
                flipkart_url = "https://www.flipkart.com/search?q="+searchString
                # requesting the webpage from the internet
                uClient = uReq(flipkart_url)
                flipkartPage = uClient.read()  # reading the webpage
                uClient.close()
                # parsing the webpage as HTML
                flipkart_html = bs(flipkartPage, "html.parser")
                # seacrhing for appropriate tag to redirect to the product link
                bigboxes = flipkart_html.findAll(
                    "div", {"class": "_1AtVbE col-12-12"})
                # the first 3 members of the list do not contain relevant information, hence deleting them
                del bigboxes[0:3]

                box = bigboxes[0]  # taking the first iteration (for demo)
                productLink = "https://www.flipkart.com" + \
                    box.div.div.div.a['href']  # extracting the actual product link

                # getting the product page from server
                prodRes = requests.get(productLink)

                # parsing the product page as HTML
                prod_html = bs(prodRes.text, "html.parser")

                # finding the HTML section containing the customer comments
                commentboxes = prod_html.find_all("div", {'class': "_16PBlm"})

                # creating a collection with the same name as search string. Tables and Collections are analogous
                table = db[searchString]

                filename = searchString+".csv"  # filename to save the details

                # creating a local file to save the details with encoding
                fw = open(filename, "w", encoding="utf-8")

                # providing the heading of the columns
                headers = "Product, Customer Name, Rating, Heading, Comment \n"

                fw.write(headers)  # writing first the headers to file
                reviews = []  # initializing an empty list for reviews

                #  iterating over the comment section to get the details of customer and their comments
                for commentbox in commentboxes:
                    try:
                        name = commentbox.div.div.find_all(
                            "p", {"class": "_2sc7ZR _2V5EHH"})[0].text
                    except:
                        name = "No Name"
                    try:
                        Rating = commentbox.div.div.div.div.text
                    except:
                        Rating = "No Rating"
                    try:
                        commentHead = commentbox.div.div.div.p.text
                    except:
                        commentHead = "No Comment Head"
                    try:
                        comtag = commentbox.div.div.find_all(
                            'div', {'class': ''})
                        custComment = comtag[0].div.text
                    except:
                        custComment = "No Customer Comment"
                    fw.write(searchString + ","+name.replace(",", ":")+","+rating+"," +
                             commentHead.replace(",", ":")+","+custComment.replace(",", ":"), +"\n")
                    mydict = {"Product": searchString, "Name": name, "Rating": Rating,
                              "CommentHead": commentHead, "Comment": custComment}  # saving that detail to a dictionary

                    # insertig the dictionary containing the review comments to the collection
                    X = table.insert_one(mydict)
                    
                    # appending the comments to the review list
                    reviews.append(mydict)
                # showing the review to the user
                return render_template("result.html", reviews=reviews)
        except Exception as e:
            print(e)
            return render_template("error.html", error=e)
    else:
        return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
