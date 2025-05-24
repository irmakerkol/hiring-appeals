from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd
import uuid, datetime, os, json
from functools import wraps

app = Flask(__name__)
app.secret_key = "secretkey"         
ADMIN_PASSWORD = "admin"               

AUDIT_LOG   = "audit_log.csv"
APPEALS_LOG = "appeals_log.csv"

def init_files():
    if not os.path.exists(AUDIT_LOG):
        pd.DataFrame(columns=['timestamp','applicant_id','features','prediction']) \
          .to_csv(AUDIT_LOG, index=False)
    if not os.path.exists(APPEALS_LOG):
        pd.DataFrame(columns=[
            'appeal_id','timestamp','applicant_id',
            'reason','status','reviewer_notes','review_timestamp'
        ]).to_csv(APPEALS_LOG, index=False)

@app.before_first_request
def setup():
    init_files()

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session['admin'] = True
            flash("Logged in successfully!", "success")
            nxt = request.args.get("next") or url_for("appeals")
            return redirect(nxt)
        else:
            flash("Wrong password", "danger")
    return render_template("login.html")

@app.route("/", methods=["GET","POST"])
def form():
    if request.method == "POST":
        applicant_id = request.form["applicant_id"]
        features     = json.dumps({k:v for k,v in request.form.items() if k!="reason"})
        prediction   = 0
        pd.DataFrame([{
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "applicant_id": applicant_id,
            "features": features,
            "prediction": prediction
        }]).to_csv(AUDIT_LOG, mode="a", header=False, index=False)

        appeal = {
            "appeal_id": str(uuid.uuid4()),
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "applicant_id": applicant_id,
            "reason": request.form["reason"],
            "status": "OPEN",
            "reviewer_notes": "",
            "review_timestamp": ""
        }
        pd.DataFrame([appeal]).to_csv(APPEALS_LOG, mode="a", header=False, index=False)
        return redirect(url_for("thank_you"))
    return render_template("form.html")

@app.route("/thankyou")
def thank_you():
    return """
      <h2>Thank you! Your appeal has been recorded.</h2>
      <p><a href='/'>Submit another</a></p>
    """

@app.route("/appeals")
@admin_required
def appeals():
    df = pd.read_csv(APPEALS_LOG)
    open_appeals = df[df["status"]=="OPEN"].to_dict(orient="records")
    return render_template("appeals.html", appeals=open_appeals)

@app.route("/resolve/<appeal_id>", methods=["GET","POST"])
@admin_required
def resolve(appeal_id):
    df = pd.read_csv(APPEALS_LOG)
    if request.method == "POST":
        idx = df.index[df["appeal_id"] == appeal_id][0]
        df.at[idx, "status"]          = request.form["status"]
        df.at[idx, "reviewer_notes"]  = request.form["notes"]
        df.at[idx, "review_timestamp"]= datetime.datetime.utcnow().isoformat()
        df.to_csv(APPEALS_LOG, index=False)
        return redirect(url_for("appeals"))
    appeal = df[df["appeal_id"] == appeal_id].iloc[0].to_dict()
    return render_template("resolve.html", appeal=appeal)

if __name__ == "__main__":
    app.run(debug=True)
