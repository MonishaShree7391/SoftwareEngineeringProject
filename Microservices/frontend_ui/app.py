#frontend_ui/app.py
from flask import Flask, render_template, request, jsonify, Response
import requests
from flask_cors import CORS

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)
print(app.url_map)
# Docker Compose service name
#AUTH_SERVICE_URL = "http://authservice:5000"
#AUTH_SERVICE_URL = "http://authservice:5000"
#INVOICE_SERVICE_URL ="http://invoiceservice:5002"
#SPLIT_SERVICE_URL = "http://splitservice:5003"
#DEBT_SERVICE_URL = "http://debtservice:5004"

#AUTH_SERVICE_URL = "http://localhost:5000"
#INVOICE_SERVICE_URL ="http://localhost:5002"
#SPLIT_SERVICE_URL = "http://localhost:5003"
#DEBT_SERVICE_URL = "http://localhost:5004"
#ADMIN_SERVICE_URL = "http://localhost:5005"

AUTH_SERVICE_URL = "https://authservice.victoriousriver-e1350c51.westus2.azurecontainerapps.io"
INVOICE_SERVICE_URL ="https://invoiceservice.victoriousriver-e1350c51.westus2.azurecontainerapps.io"
SPLIT_SERVICE_URL = "https://splitservice.victoriousriver-e1350c51.westus2.azurecontainerapps.io"
DEBT_SERVICE_URL = "https://debtservice.victoriousriver-e1350c51.westus2.azurecontainerapps.io"
ADMIN_SERVICE_URL = "https://adminservice.victoriousriver-e1350c51.westus2.azurecontainerapps.io"

# ---------- HTML ROUTES ----------
#@app.route("/index.html")
@app.route("/index")
def home():
    return render_template("index.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/signup")
def signup_page():
    return render_template("signup.html")

@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")

@app.route("/settings")
def settings_page():
    return render_template("settings.html")

@app.route("/admin_dashboard.html")
def admin_page():
    return render_template("admin_dashboard.html")

@app.route("/admin_settlements.html")
def admin_settlements_page():
    return render_template("admin_settlements.html")

#@app.route("/debt/balances", methods=["GET"])
#def show_balances_html():
    #return render_template("balances.html")


# <- ensure this template exists

# ---------- API PROXIES ----------
@app.route("/auth/login", methods=["POST"])
def proxy_login():
    try:
        resp = requests.post(f"{AUTH_SERVICE_URL}/auth/login", json=request.get_json())
        print("RAW backend response: login: ", resp.text)
        if not resp.headers.get("Content-Type", "").startswith("application/json"):
            return jsonify({"error": "Backend error (not JSON)"}), 500
        return (resp.content, resp.status_code, resp.headers.items())
        #return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException:
        return jsonify({"error": "Auth service unreachable"}), 503

@app.route("/auth/signup", methods=["POST"])
def proxy_signup():
    try:
        resp = requests.post(f"{AUTH_SERVICE_URL}/auth/signup", json=request.get_json())
        print("RAW backend response:signup:", resp.text)
        if not resp.headers.get("Content-Type", "").startswith("application/json"):
            return jsonify({"error": "Backend error (not JSON)"}), 500
        print('hitting signup','resp.status_code',resp.status_code)
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException:
        return jsonify({"error": "Auth service unreachable"}), 503

@app.route("/auth/profile", methods=["GET"])
def proxy_profile():
    auth_header = request.headers.get("Authorization")
    try:
        resp = requests.get(
            f"{AUTH_SERVICE_URL}/auth/profile",
            headers={"Authorization": auth_header} if auth_header else {}
        )
        print("RAW backend response:Profile: ", resp.text)
        if not resp.headers.get("Content-Type", "").startswith("application/json"):
            return jsonify({"error": "Backend error (not JSON)"}), 500
        #resp.headers.add('Access-Control-Allow-Origin', '*')
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException:
        return jsonify({"error": "Auth service unreachable"}), 503

@app.route("/auth/logout", methods=["POST"])
def proxy_logout():
    auth_header = request.headers.get("Authorization")
    try:
        resp = requests.post(
            f"{AUTH_SERVICE_URL}/auth/logout",
            headers={"Authorization": auth_header} if auth_header else {}
        )
        #resp.headers.add('Access-Control-Allow-Origin', '*')
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException:
        return jsonify({"error": "Auth service unreachable"}), 503

@app.route("/profile")
def profile_page():
    return render_template("profile.html")
@app.route("/view")
def view_page():
    return render_template("view.html")

@app.route("/view_invoices_month.html")
def view_invoices_month_page():
    return render_template("view_invoices_month.html")

@app.route("/split_invoice.html")
def split_invoice_page():
    return render_template("split_invoice.html")

@app.route("/balances.html", methods=["GET"])
def render_balances_page():
    return render_template("balances.html")
####INVOICE PROXY

  # or whatever port it's on

#INVOICE_SERVICE_URL = "http://invoiceservice:5002"
@app.route("/invoice/static/uploads/<int:year>/<month>/<filename>")
def proxy_pdf_file(year, month, filename):
    try:
        # Construct the URL to the actual PDF location on the backend service
        # This assumes your invoice service has a route or static file serving
        # at this exact path for PDFs.
        backend_pdf_url = f"{INVOICE_SERVICE_URL}/static/uploads/{year}/{month}/{filename}"
        print(f"Proxying request to backend: {backend_pdf_url}") # For debugging

        # Add Authorization header if your backend /invoice/static/uploads endpoint requires it
        auth_header = request.headers.get("Authorization")
        headers = {"Authorization": auth_header} if auth_header else {}


        resp = requests.get(
            backend_pdf_url,
            stream=True, # Important for large files
            headers=headers # Pass along the auth header
        )
        resp.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        # Ensure correct Content-Type is passed back to the client
        # It's safer to get Content-Type from the backend response
        content_type = resp.headers.get("Content-Type", "application/octet-stream")

        return Response(resp.iter_content(chunk_size=1024), content_type=content_type)
    except requests.exceptions.RequestException as e:
        print(f"Error during PDF proxy request: {e}")
        # Return a proper error response if backend is unreachable or returns an error
        if e.response is not None:
            return Response(e.response.content, status=e.response.status_code, content_type=e.response.headers.get("Content-Type", "application/json"))
        return jsonify({"error": "Failed to retrieve PDF", "details": str(e)}), 500
    except Exception as e:
        print(f"Unexpected error in proxy_pdf_file: {e}")
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

@app.route("/invoice/view_invoices_by_month")
def proxy_view_by_month():
    auth_header = request.headers.get("Authorization")
    print(">>> Incoming Authorization header:", auth_header)
    try:
        response = requests.get(
            f"{INVOICE_SERVICE_URL}/invoice/view_invoices_by_month",
            headers={"Authorization": auth_header} if auth_header else {},
            params=request.args
        )
        print("RAW backend response: view_invoices_by_month: ", response.text)
        return (response.content, response.status_code, response.headers.items())
    except requests.exceptions.RequestException as e:
        print("Proxy error:", e)
        return jsonify({"error": "Invoice service unreachable"}), 503

@app.route("/invoice/view_data_by_date")
def proxy_view_data_by_date():
    auth_header = request.headers.get("Authorization")
    try:
        resp = requests.get(
            f"{INVOICE_SERVICE_URL}/invoice/view_data_by_date",
            headers={"Authorization": auth_header} if auth_header else {},
            params=request.args
        )
        print("RAW backend response:view_data_by_date: ", resp.text)
        #if not resp.headers.get("Content-Type", "").startswith("application/json"):
            #return jsonify({"error": "view_data_by_date: Backend error (not JSON)"}), 500
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException:
        return jsonify({"error": "Invoice service unreachable"}), 503

@app.route("/invoice/view")
def proxy_view_data():
    auth_header = request.headers.get("Authorization")
    try:
        resp = requests.get(
            f"{INVOICE_SERVICE_URL}/invoice/view",
            headers={"Authorization": auth_header} if auth_header else {},
            params=request.args
        )
        print("RAW backend response:view : ", resp.text)
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Invoice service unreachable", "details": str(e)}), 503


@app.route("/invoice/get_invoice_years")
def proxy_invoice_years():
    auth_header = request.headers.get("Authorization")
    try:
        response = requests.get(
            f"{INVOICE_SERVICE_URL}/invoice/get_invoice_years",
            headers={"Authorization": auth_header} if auth_header else {}
        )
        print("RAW backend response: get_invoice_years: ", response.text)
        #if not response.headers.get("Content-Type", "").startswith("text/html"):
        return (response.content, response.status_code, response.headers.items())
    except Exception as e:
        return jsonify({"error": f"Year list fetch failed: {str(e)}"}), 500

@app.route("/invoice/get_invoice_months/<int:year>")
def proxy_invoice_months(year):
    auth_header = request.headers.get("Authorization")
    print(">>> Incoming Authorization header:", auth_header)
    try:
        response = requests.get(
            f"{INVOICE_SERVICE_URL}/invoice/get_invoice_months/{year}",
            headers={"Authorization": auth_header} if auth_header else {},
            params=request.args
        )
        print("RAW backend response:get_invoice_months: ", response.text)
        #if not response.headers.get("Content-Type", "").startswith("text/html"):
            #return render_template("view_data.html", message="view_data: Unexpected content type from backend")
        return (response.content, response.status_code, response.headers.items())
    except Exception as e:
        return jsonify({"error": f"Month list fetch failed: {str(e)}"}), 500

@app.route("/invoice/upload", methods=["POST"])
def proxy_invoice_upload():
    auth_header = request.headers.get("Authorization")
    data = request.form.to_dict()
    file = request.files.get("file")

    try:
        files = {"file": (file.filename, file.stream, file.content_type)} if file else {}

        response = requests.post(
                f"{INVOICE_SERVICE_URL}/invoice/upload",
                headers={"Authorization": auth_header} if auth_header else {},
                data=data,
                files=files
            )

        print("RAW backend response: invoice_upload:", response.text)
        return (response.content, response.status_code, response.headers.items())

    except requests.exceptions.RequestException:
        return jsonify({"error": "Invoice service unreachable"}), 503


@app.route("/invoice/check_filename", methods=["POST"])
def proxy_check_filename():
    auth_header = request.headers.get("Authorization")
    print(">>> Incoming Authorization header:", auth_header)
    try:
        # If frontend sends JSON, forward JSON
        resp = requests.post(
            f"{INVOICE_SERVICE_URL}/invoice/check_filename",
            headers={"Authorization": auth_header, "Content-Type": "application/json"} if auth_header else {"Content-Type": "application/json"},
            json=request.get_json() # Use json= for JSON data
        )
        print("RAW backend response:check_filename: ", resp.text)
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException as e:
        print(f"Proxy request failed: {e}")
        return jsonify({"error": "Invoice service unreachable"}), 503

#############################################################################################################
#                      split service
######################################################################################################
# --- Split Service Proxies ---
@app.route("/split/add_split_invoice_user", methods=["POST"])
def proxy_add_split_user():
    print('\ninside add_split_invoice_user proxy\n')
    auth_header = request.headers.get("Authorization")

    try:
        resp = requests.post(
            f"{SPLIT_SERVICE_URL}/split/add_split_invoice_user",
            headers={"Authorization": auth_header, "Content-Type": "application/json"} if auth_header else {"Content-Type": "application/json"},
            json=request.get_json()
        )
        print("\n RAW backend response: add_split_user: ", resp.text)
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException as e:
        print(f"Proxy request failed for add_split_user: {e}")
        return jsonify({"error": "Split service unreachable"}), 503

@app.route("/split/my_split_users", methods=["GET"])
def proxy_my_split_users():
    print('inside my_split_users proxy')
    auth_header = request.headers.get("Authorization")
    try:
        resp = requests.get(
            f"{SPLIT_SERVICE_URL}/split/my_split_users",
            headers={"Authorization": auth_header} if auth_header else {},
            params=request.args
        )
        print("RAW backend response: my_split_users: ", resp.text)
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException as e:
        print(f"Proxy request failed for my_split_users: {e}")
        return jsonify({"error": "Split service unreachable"}), 503

@app.route("/split/split_invoice", methods=["GET"])
def proxy_split_invoice_get():
    auth_header = request.headers.get("Authorization")
    try:
        resp = requests.get(
            f"{SPLIT_SERVICE_URL}/split/split_invoice",
            headers={
                "Authorization": auth_header,
                "Accept": "application/json"
            },
            params=request.args
        )
        print("RAW backend response: split_invoice GET: ", resp.text)
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException as e:
        print(f"Split proxy GET failed: {e}")
        return jsonify({"error": "Split service unreachable"}), 503

@app.route("/split/split_invoice", methods=["POST"])
def proxy_split_invoice_post():
    auth_header = request.headers.get("Authorization")
    try:
        resp = requests.post(
            f"{SPLIT_SERVICE_URL}/split/split_invoice",
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/json"
            },
            json=request.get_json()
        )
        print("RAW backend response: split_invoice POST: ", resp.text)
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException as e:
        print(f"Split proxy POST failed: {e}")
        return jsonify({"error": "Split service unreachable"}), 503





@app.route("/api/split_users", methods=["GET"])
def proxy_get_split_users():
    auth_header = request.headers.get("Authorization")
    try:
        resp = requests.get(
            f"{SPLIT_SERVICE_URL}/api/split_users",
            headers={"Authorization": auth_header} if auth_header else {},
            params=request.args
        )
        print("RAW backend response: get_split_users: ", resp.text)
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException as e:
        print(f"Proxy request failed for get_split_users: {e}")
        return jsonify({"error": "Split service unreachable"}), 503

####################################################################
#DEBT_SERVICE
#####################################
@app.route("/debt/balances", methods=["GET"])
def proxy_balances():
    try:
        print("Authorization header:", request.headers.get("Authorization"))
        token = request.headers.get("Authorization")
        resp = requests.get(
            f"{DEBT_SERVICE_URL}/debt/balances",
            headers={"Authorization": token} if token else {}
        )
        print("\n RAW backend response: balances: ", resp.text,"\n")
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException:
        return jsonify({"error": "Debt service unreachable"}), 503

@app.route("/debt/settle_debt", methods=["POST"])
def proxy_settle_debt():
    print("\n>>> [Frontend] Received POST /debt/settle_debt")
    try:
        token = request.headers.get("Authorization")
        resp = requests.post(
            f"{DEBT_SERVICE_URL}/debt/settle_debt",
            json=request.get_json(),
            headers={"Authorization": token} if token else {}
        )
        print(">>> [Proxy] Debt service responded with:", resp.status_code, resp.text)
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException:
        return jsonify({"error": "Debt service unreachable"}), 503

@app.route("/settlement_history.html")
def settlement_history_page():
    return render_template("settlement_history.html")


@app.route("/debt/settlement_log")
def proxy_settlement_log():
    auth_header = request.headers.get("Authorization")
    try:
        resp = requests.get(
            f"{DEBT_SERVICE_URL}/debt/settlement_log",  # or localhost if monolithic
            headers={"Authorization": auth_header} if auth_header else {}
        )
        #resp.headers.add("Access-Control-Allow-Origin", "*")
        print(">>> [Proxy] settlement_log  responded with:", resp.status_code, resp.text)
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException:
        return jsonify({"error": "Debt service unreachable"}), 503
########################################
# ADMIN SERVICE - User Management
########################################
@app.route("/admin/api/settlements", methods=["GET"])
def proxy_admin_api_settlements():
    auth_header = request.headers.get("Authorization")
    try:
        resp = requests.get(
            f"{ADMIN_SERVICE_URL}/admin/api/settlements",
            headers={"Authorization": auth_header} if auth_header else {}
        )
        print("RAW backend response: /admin/api/settlements:", resp.status_code)
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException as e:
        print(" Proxy error:", e)
        return jsonify({"error": "Admin service unreachable"}), 503

@app.route("/admin/users/promote/<int:user_id>", methods=["POST"])
def proxy_admin_promote_user(user_id):
    auth_header = request.headers.get("Authorization")
    try:
        resp = requests.post(
            f"{ADMIN_SERVICE_URL}/admin/users/promote/{user_id}",
            headers={"Authorization": auth_header} if auth_header else {}
        )
        print("RAW backend response: promote_user:", resp.text)
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException:
        return jsonify({"error": "Admin service unreachable"}), 503

@app.route("/admin/users/demote/<int:user_id>", methods=["POST"])
def proxy_admin_demote_user(user_id):
    auth_header = request.headers.get("Authorization")
    try:
        resp = requests.post(
            f"{ADMIN_SERVICE_URL}/admin/users/demote/{user_id}",
            headers={"Authorization": auth_header} if auth_header else {}
        )
        print("RAW backend response: demote_user:", resp.text)
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException:
        return jsonify({"error": "Admin service unreachable"}), 503

@app.route("/admin/users/delete/<int:user_id>", methods=["POST"])
def proxy_admin_delete_user(user_id):
    auth_header = request.headers.get("Authorization")
    try:
        resp = requests.post(
            f"{ADMIN_SERVICE_URL}/admin/users/delete/{user_id}",
            headers={"Authorization": auth_header} if auth_header else {}
        )
        print("RAW backend response: delete_user:", resp.text)
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException:
        return jsonify({"error": "Admin service unreachable"}), 503

########################################
# ADMIN SERVICE - Settlement Management
########################################

@app.route("/admin/settlements/complete/<int:settlement_id>", methods=["POST"])
def proxy_admin_settlement_complete(settlement_id):
    auth_header = request.headers.get("Authorization")
    try:
        resp = requests.post(
            f"{ADMIN_SERVICE_URL}/admin/settlements/complete/{settlement_id}",
            headers={"Authorization": auth_header} if auth_header else {}
        )
        print("RAW backend response: mark_settlement_complete:", resp.text)
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException:
        return jsonify({"error": "Admin service unreachable"}), 503

@app.route("/admin/settlements/delete/<int:settlement_id>", methods=["POST"])
def proxy_admin_delete_settlement(settlement_id):
    auth_header = request.headers.get("Authorization")
    try:
        resp = requests.post(
            f"{ADMIN_SERVICE_URL}/admin/settlements/delete/{settlement_id}",
            headers={"Authorization": auth_header} if auth_header else {}
        )
        print("RAW backend response: delete_settlement:", resp.text)
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException:
        return jsonify({"error": "Admin service unreachable"}), 503

@app.route("/split/settlement/summary", methods=["GET"])
def proxy_split_settlement_summary():
    auth_header = request.headers.get("Authorization")
    try:
        resp = requests.get(
            f"{SPLIT_SERVICE_URL}/split/settlement/summary",
            headers={"Authorization": auth_header} if auth_header else {}
        )
        print("RAW backend response: settlement summary:", resp.text)
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException as e:
        print(f"Split proxy failed: {e}")
        return jsonify({"error": "Split service unreachable"}), 503

@app.route("/admin/total_users", methods=["GET"])
def proxy_admin_total_users():
    auth_header = request.headers.get("Authorization")
    try:
        resp = requests.get(
            f"{ADMIN_SERVICE_URL}/admin/total_users",
            headers={"Authorization": auth_header} if auth_header else {}
        )
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException:
        return jsonify({"error": "Admin service unreachable"}), 503

@app.route("/admin/total_invoices", methods=["GET"])
def proxy_admin_total_invoices():
    auth_header = request.headers.get("Authorization")
    try:
        resp = requests.get(
            f"{ADMIN_SERVICE_URL}/admin/total_invoices",
            headers={"Authorization": auth_header} if auth_header else {}
        )
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException:
        return jsonify({"error": "Admin service unreachable"}), 503

@app.route("/admin/total_splits", methods=["GET"])
def proxy_admin_total_splits():
    auth_header = request.headers.get("Authorization")
    try:
        resp = requests.get(
            f"{ADMIN_SERVICE_URL}/admin/total_splits",
            headers={"Authorization": auth_header} if auth_header else {}
        )
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException:
        return jsonify({"error": "Admin service unreachable"}), 503

@app.route("/admin/total_settled", methods=["GET"])
def proxy_admin_total_settled():
    auth_header = request.headers.get("Authorization")
    try:
        resp = requests.get(
            f"{ADMIN_SERVICE_URL}/admin/total_settled",
            headers={"Authorization": auth_header} if auth_header else {}
        )
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException:
        return jsonify({"error": "Admin service unreachable"}), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)