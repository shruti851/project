from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from bson import ObjectId
from ai_engine import match_startup_investors, match_talent

app = Flask(__name__)
app.secret_key = "startup_secret"

# ---------------- MONGODB CONNECTION ----------------
client = MongoClient("mongodb://localhost:27017/")
db = client["startup_ecosystem"]

users_col = db["users"]
startups_col = db["startups"]
roles_col = db["roles"]
applications_col = db["applications"]
funding_requests_col = db["funding_requests"]
funding_decisions_col = db["funding_decisions"]
investments_col = db["investments"]
feedback_col = db["ai_feedback"]
matches_col = db["ai_matches"]

# =====================================================
# HOME
# =====================================================

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('home.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# =====================================================
# REGISTER
# =====================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users_col.insert_one({
            "name": request.form['name'],
            "email": request.form['email'],
            "password": request.form['password'],
            "role": request.form['role']
        })
        return redirect(url_for('login'))

    return render_template('register.html')


# =====================================================
# LOGIN
# =====================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = users_col.find_one({
            "email": request.form['email'],
            "password": request.form['password']
        })

        if user:
            session['user_id'] = str(user['_id'])
            session['role'] = user['role']
            session['name'] = user['name']
            return redirect(url_for('dashboard'))

        return "Invalid Credentials"

    return render_template('login.html')


# =====================================================
# DASHBOARD (DYNAMIC + FIXED)
# =====================================================

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    role = session['role']
    user_id = session['user_id']

    stats = {
        "startups": startups_col.count_documents({}) if role != "Founder" else startups_col.count_documents({"founder_id": user_id}),
        "funding": funding_requests_col.count_documents({"founder_id": user_id}) if role == "Founder" else investments_col.count_documents({"investor_id": user_id}) if role == "Investor" else applications_col.count_documents({"talent_id": user_id}),
        "users": users_col.count_documents({})
    }

    # Create labels and data for chart - use generic names
    labels = ["Startups", "Active Items", "Users"]
    chart_data = [stats["startups"], stats["funding"], stats["users"]]

    return render_template(
        "dashboard.html",
        name=session['name'],
        role=role,
        stats=stats,
        chart_data=chart_data,
        chart_labels=labels
    )


# =====================================================
# PITCH STARTUP
# =====================================================

@app.route('/pitch', methods=['GET', 'POST'])
def pitch():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        startups_col.insert_one({
            "title": request.form['title'],
            "domain": request.form['domain'],
            "description": request.form['description'],
            "funding": int(request.form['funding']),
            "founder_id": session['user_id']
        })

        return redirect(url_for('dashboard'))

    return render_template('pitch_idea.html')


# =====================================================
# VIEW STARTUPS (FOUNDER)
# =====================================================

@app.route('/view_startups')
def view_startups():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    startups = startups_col.find({
        "founder_id": session['user_id']
    })

    return render_template('view_startups.html', startups=startups)


# =====================================================
# CREATE ROLE
# =====================================================

@app.route('/create-role', methods=['GET', 'POST'])
def create_role():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        roles_col.insert_one({
            "startup_title": request.form['startup_title'],
            "role_name": request.form['role_name'],
            "skills": request.form['skills'],
            "founder_id": session['user_id']
        })

        return redirect(url_for('view_roles'))

    return render_template('create_role.html')


# =====================================================
# VIEW ROLES
# =====================================================

@app.route('/view_roles')
def view_roles():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    roles = roles_col.find()

    return render_template('view_roles.html', roles=roles)



# =====================================================
# APPLY ROLE (FIXED TALENT ID)
# =====================================================

@app.route('/apply/<role_id>', methods=['GET', 'POST'])
def apply_role(role_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if session['role'] != "Talent":
        return "Access Denied"

    role = roles_col.find_one({"_id": ObjectId(role_id)})

    if not role:
        return "Role Not Found"

    if request.method == 'POST':
        applications_col.insert_one({
            "role_id": role_id,
            "talent_id": session['user_id'],
            "talent_name": session['name'],
            "email": request.form['email'],
            "skills": request.form['skills'],
            "status": "Pending"
        })

        return redirect(url_for('my_applications'))

    return render_template('apply_role.html', role=role)

@app.route('/my-applications')
def my_applications():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if session['role'] != "Talent":
        return "Access Denied"

    applications = list(applications_col.find({
        "talent_id": session['user_id']
    }))

    for app in applications:
        role = roles_col.find_one({"_id": ObjectId(app["role_id"])})
        app["role_name"] = role["role_name"] if role else "Unknown"

    return render_template(
        "my_applications.html",
        applications=applications
    )

@app.route('/ai/talent-match/<startup_id>')
def ai_talent_match(startup_id):
    startup = startups_col.find_one({"_id": ObjectId(startup_id)})
    talents = list(users_col.find({"role": "Talent"}))

    matches = match_talent(
        startup.get("description", ""),
        talents
    )

    return render_template(
        "talent_match.html",
        startup=startup,
        matches=matches
    )



# =====================================================
# INVESTOR VIEW STARTUPS
# =====================================================

@app.route('/investor/startups')
def investor_view_startups():
    startups = startups_col.find()
    return render_template('investor_startups.html', startups=startups)


# =====================================================
# INVEST
# =====================================================

@app.route('/invest/<startup_id>', methods=['POST'])
def invest(startup_id):
    investments_col.insert_one({
        "startup_id": startup_id,
        "investor_id": session['user_id'],
        "amount": request.form['amount'],
        "status": "Approved"
    })

    return redirect(url_for('investor_portfolio'))


# =====================================================
# INVESTOR PORTFOLIO (FIXED JOIN)
# =====================================================

@app.route('/investor/portfolio')
def investor_portfolio():
    investments = list(investments_col.find({
        "investor_id": session['user_id']
    }))

    for inv in investments:
        startup = startups_col.find_one({"_id": ObjectId(inv["startup_id"])})
        inv["startup_title"] = startup["title"] if startup else "Unknown"

    return render_template(
        "investor_portfolio.html",
        investments=investments
    )


# =====================================================
# ANALYTICS (REAL COUNTS)
# =====================================================

@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect('/login')

    role = session['role']
    user_id = session['user_id']
    
    # Base data available to all roles
    data = {
        "total_startups": startups_col.count_documents({}),
        "total_users": users_col.count_documents({}),
        "total_investments": investments_col.count_documents({}),
        "total_roles": roles_col.count_documents({})
    }
    
    # Role-specific data
    if role == "Founder":
        data.update({
            "my_startups": startups_col.count_documents({"founder_id": user_id}),
            "funding_requests": funding_requests_col.count_documents({"founder_id": user_id}),
            "my_roles": roles_col.count_documents({"founder_id": user_id}),
            "applications_received": applications_col.count_documents({})
        })
    elif role == "Investor":
        data.update({
            "my_investments": investments_col.count_documents({"investor_id": user_id}),
            "my_portfolio_value": sum([int(inv.get("amount", 0)) for inv in investments_col.find({"investor_id": user_id})]),
            "funded_startups": len(list({inv["startup_id"] for inv in investments_col.find({"investor_id": user_id})}))
        })
    elif role == "Talent":
        data.update({
            "my_applications": applications_col.count_documents({"talent_id": user_id}),
            "available_roles": roles_col.count_documents({}),
            "applications_approved": applications_col.count_documents({"talent_id": user_id, "status": "Approved"})
        })

    return render_template(
        "analytics.html",
        analytics=data,
        role=role
    )


# =====================================================
# AI MATCH
# =====================================================

@app.route('/ai/investor-match/<startup_id>')
def investor_match(startup_id):
    startup = startups_col.find_one({"_id": ObjectId(startup_id)})
    investors = list(users_col.find({"role": "Investor"}))

    matches = match_startup_investors(
        startup["description"],
        investors
    )

    return render_template(
        "investor_match.html",
        startup=startup,
        matches=matches
    )



# =====================================================
# MISSING ROUTES
# =====================================================

@app.route('/view_funding_requests')
def view_funding_requests():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    funding_requests = list(funding_requests_col.find({"founder_id": session['user_id']}))
    return render_template('view_funding_requests.html', funding_requests=funding_requests)


@app.route('/ai_skill_match')
def ai_skill_match():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session['role'] != "Talent":
        return "Access Denied"
    
    roles = list(roles_col.find())
    return render_template('ai_skill_match.html', roles=roles)


@app.route('/market_insights')
def market_insights():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    data = {
        "total_startups": startups_col.count_documents({}),
        "total_investments": investments_col.count_documents({}),
        "total_roles": roles_col.count_documents({}),
        "total_users": users_col.count_documents({})
    }
    
    return render_template('market_insights.html', data=data, role=session['role'])


@app.route('/update_startup/<startup_id>', methods=['GET', 'POST'])
def update_startup(startup_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    startup = startups_col.find_one({"_id": ObjectId(startup_id)})
    
    if not startup or startup['founder_id'] != session['user_id']:
        return "Access Denied"
    
    if request.method == 'POST':
        startups_col.update_one(
            {"_id": ObjectId(startup_id)},
            {"$set": {
                "title": request.form['title'],
                "domain": request.form['domain'],
                "description": request.form['description'],
                "funding": int(request.form['funding'])
            }}
        )
        return redirect(url_for('view_startups'))
    
    return render_template('update_startup.html', startup=startup)


@app.route('/fund_startup/<startup_id>', methods=['GET', 'POST'])
def fund_startup(startup_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session['role'] != "Investor":
        return "Access Denied"
    
    startup = startups_col.find_one({"_id": ObjectId(startup_id)})
    
    if not startup:
        return "Startup Not Found"
    
    if request.method == 'POST':
        investments_col.insert_one({
            "startup_id": startup_id,
            "investor_id": session['user_id'],
            "amount": int(request.form['amount']),
            "status": "Approved"
        })
        return redirect(url_for('investor_portfolio'))
    
    return render_template('fund_startup.html', startup=startup)


# =====================================================
# RUN APP
# =====================================================

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
