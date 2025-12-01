from server import MiniExpress

app = MiniExpress()

# In-memory database (list of objects)
database = []

# STATIC FILES
# Serve files from ./static at URL path /static
app.use_static('/static', './static')

# BASIC ROUTES
@app.get("/")
def home(req, res):
    res.send("Welcome to MiniExpress!")


@app.get("/echo")
def echo(req, res):
    # Example of reading query parameters
    message = req.query.get("message", "No message provided")
    res.send(f"Echo: {message}")


@app.get("/user/:id")
def get_user(req, res):
    # Example of reading path parameter and returning JSON
    user_id = req.params.get("id")
    res.json({"user_id": user_id})



# REQUIRED ASSIGNMENT API ROUTES

# POST /data → add new JSON object to memory
@app.post("/data")
def create_data(req, res):
    body = req.body  # parsed JSON from request

    if not isinstance(body, dict):
        return res.status(400).send("Invalid JSON!")

    # Assign an ID
    new_id = len(database) + 1

    # Store object
    new_item = {"id": new_id, "data": body}
    database.append(new_item)

    # Return success with ID
    res.status(201).json({"id": new_id})


# GET /data → return all stored objects
@app.get("/data")
def get_all_data(req, res):
    res.json(database)


# GET /data/:id → return single object by ID
@app.get("/data/:id")
def get_data_by_id(req, res):
    try:
        data_id = int(req.params.get("id"))
    except:
        return res.status(400).send("Invalid ID!")

    # Find item
    for item in database:
        if item["id"] == data_id:
            return res.json(item)

    # If not found --> gives error message 
    res.status(404).send("Item not found")


# START SERVER
app.listen(8080)
