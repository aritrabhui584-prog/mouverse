from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_login import login_required, current_user
import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

region_bp = Blueprint("region", __name__)

# Region-to-language mappings as requested by user
REGION_LANGUAGES = {
    "India": ["Hindi", "Bengali", "Tamil", "Telugu", "Marathi", "Urdu", "Malayalam", "Kannada", "Punjabi"],
    "USA": ["English", "Spanish"],
    "UK": ["English"],
    "Korea": ["Korean"],
    "Japan": ["Japanese"],
    "Bangladesh": ["Bengali"],
    "Pakistan": ["Urdu", "Punjabi"]
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "mouverse.db")

def update_user_region(user_id, region):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET region = ? WHERE id = ?", (region, user_id))
    conn.commit()
    conn.close()

@region_bp.route("/region-select", methods=["GET", "POST"])
@login_required
def select_region():
    if request.method == "POST":
        selected_region = request.form.get("region")
        if selected_region in REGION_LANGUAGES:
            # Store selected region in session
            session["region"] = selected_region
            
            # Update user region in database
            try:
                update_user_region(current_user.id, selected_region)
            except Exception as e:
                logger.error(f"Error updating user region: {e}")
                
            flash(f"Region set to {selected_region}!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid region selected.", "danger")
            
    # List of available regions for template rendering
    return render_template(
        "region_select.html", 
        regions=list(REGION_LANGUAGES.keys()), 
        current_region=session.get("region") or current_user.region
    )
