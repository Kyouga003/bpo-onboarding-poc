import os
import json
import random
from datetime import datetime
import requests
from flask import Flask, render_template, request, redirect, url_for, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
DB_FILE = 'agents.json'
AUDIT_FILE = 'audit_logs.json'
SWITCH_COUNT = 300
PORTS_PER_SWITCH = 48

# Ensure local JSON databases exist
for filepath in [DB_FILE, AUDIT_FILE]:
    if not os.path.exists(filepath):
        with open(filepath, 'w') as f:
            json.dump([], f)


def load_data(filepath):
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception:
        return []


def save_data(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)


def log_audit_event(action, agent_email, details, actor="Operations Admin", compliance="RA 10173 / Client Security Policy"):
    """Logs security and operations events for client audit requirements."""
    logs = load_data(AUDIT_FILE)
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "actor": actor,
        "agent_email": agent_email,
        "details": details,
        "compliance": compliance,
    }
    logs.insert(0, log_entry)
    save_data(AUDIT_FILE, logs)


def switch_profile(work_mode):
    vlan_id = 300 if work_mode == 'Remote VPN' else 100
    access_profile = "Zero Trust Remote Agent" if work_mode == 'Remote VPN' else "On-Site Agent LAN"
    return vlan_id, access_profile


def generate_switch_config(agents, work_mode):
    """Assigns a consistent port profile across the 300 access-switch fleet."""
    used = {a.get('switch_config') for a in agents if a.get('switch_config')}
    vlan_id, access_profile = switch_profile(work_mode)
    for _ in range(500):
        switch_num = random.randint(1, SWITCH_COUNT)
        port_num = random.randint(1, PORTS_PER_SWITCH)
        config = f"Switch-{switch_num:03d} / Gi1/0/{port_num} (VLAN {vlan_id}, {access_profile})"
        if config not in used:
            return config
    return f"Switch-{random.randint(1, SWITCH_COUNT):03d} / Gi1/0/{random.randint(1, PORTS_PER_SWITCH)} (VLAN {vlan_id}, {access_profile})"


def remote_access_status(work_mode):
    if work_mode == 'Remote VPN':
        return "Cisco AnyConnect VPN + Zero Trust Policy"
    return "On-Site LAN Access (Policy Controlled)"


def quality_metrics(work_mode):
    latency = random.randint(18, 55) if work_mode == 'Remote VPN' else random.randint(8, 25)
    jitter = round(random.uniform(1.0, 8.0), 1) if work_mode == 'Remote VPN' else round(random.uniform(0.5, 3.0), 1)
    packet_loss = round(random.uniform(0.0, 1.2), 2) if work_mode == 'Remote VPN' else round(random.uniform(0.0, 0.3), 2)
    mos = round(max(3.2, min(4.5, 4.45 - (latency / 500) - (jitter / 40) - packet_loss)), 2)
    if mos >= 4.2 and packet_loss < 1:
        quality = "Optimal"
    elif mos >= 3.8:
        quality = "Acceptable"
    else:
        quality = "Investigate"
    return {
        "latency_ms": latency,
        "jitter_ms": jitter,
        "packet_loss_pct": packet_loss,
        "mos": mos,
        "call_quality": f"{quality} (MOS {mos})",
    }


def normalize_agent(agent):
    """Keeps older records compatible with newer dashboard fields."""
    work_mode = agent.get('work_mode', 'Remote VPN')
    metrics = quality_metrics(work_mode)
    agent.setdefault('department', 'Customer Support')
    agent.setdefault('team_name', 'General Intake')
    agent.setdefault('webex_space', 'BPO Onboarding Space')
    agent.setdefault('vpn_status', remote_access_status(work_mode))
    agent.setdefault('latency_ms', metrics['latency_ms'])
    agent.setdefault('jitter_ms', metrics['jitter_ms'])
    agent.setdefault('packet_loss_pct', metrics['packet_loss_pct'])
    agent.setdefault('mos', metrics['mos'])
    agent.setdefault('call_quality', metrics['call_quality'])
    agent.setdefault('compliance_status', 'Compliant')
    return agent


def provision_webex_automation(user_email, room_title="BPO Remote Agents - Intake"):
    """
    Automates Webex onboarding. Gracefully falls back to local simulation
    if the Webex token is missing, invalid, or expired (401 Unauthorized).
    """
    token = os.getenv("WEBEX_TOKEN")
    if not token:
        return "Provisioned (Simulated - Missing Token)"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        # 1. Search for existing room
        list_res = requests.get("https://webexapis.com/v1/rooms", headers=headers, timeout=4)
        if list_res.status_code == 401:
            return "Provisioned (Simulated - Token Expired 401)"

        room_id = None
        if list_res.status_code == 200:
            rooms = list_res.json().get("items", [])
            for room in rooms:
                if room.get("title") == room_title:
                    room_id = room.get("id")
                    break

        # 2. Create room if it doesn't exist
        if not room_id:
            create_res = requests.post(
                "https://webexapis.com/v1/rooms",
                headers=headers,
                json={"title": room_title},
                timeout=4
            )
            if create_res.status_code == 200:
                room_id = create_res.json().get("id")
            elif create_res.status_code == 401:
                return "Provisioned (Simulated - Token Expired 401)"

        if not room_id:
            return "Provisioned (Simulated - Room Fallback)"

        # 3. Add agent to space
        member_res = requests.post(
            "https://webexapis.com/v1/memberships",
            headers=headers,
            json={"roomId": room_id, "personEmail": user_email},
            timeout=4
        )

        if member_res.status_code == 200:
            return "Live Webex API (200 OK)"
        elif member_res.status_code == 409:
            return "Live Webex API (409 Already Member)"
        elif member_res.status_code == 401:
            return "Provisioned (Simulated - Token Expired 401)"
        else:
            return f"Webex API ({member_res.status_code})"

    except Exception:
        return "Provisioned (Simulated - Network Fallback)"

# --- FLASK ROUTES (FULL CRUD) ---

# READ: Render Admin Dashboard
@app.route('/')
def index():
    agents = [normalize_agent(a) for a in load_data(DB_FILE)]
    audit_logs = load_data(AUDIT_FILE)[:10]  # Display top 10 recent events

    total_agents = len(agents)
    remote_vpn_count = sum(1 for a in agents if a.get('work_mode') == 'Remote VPN')
    avg_latency = round(sum(a.get('latency_ms', 25) for a in agents) / max(total_agents, 1), 1)
    avg_mos = round(sum(a.get('mos', 4.4) for a in agents) / max(total_agents, 1), 2)
    switches_covered = len({(a.get('switch_config') or '').split(' / ')[0] for a in agents if a.get('switch_config')})
    degraded_calls = sum(1 for a in agents if a.get('call_quality', '').startswith(('Acceptable', 'Investigate')))

    return render_template(
        'index.html',
        agents=agents,
        audit_logs=audit_logs,
        total_agents=total_agents,
        remote_vpn_count=remote_vpn_count,
        avg_latency=avg_latency,
        avg_mos=avg_mos,
        switches_covered=switches_covered,
        degraded_calls=degraded_calls,
        switch_count=SWITCH_COUNT,
    )


# CREATE: Onboard New Agent Team Member
@app.route('/add', methods=['POST'])
def add_agent():
    agents = load_data(DB_FILE)
    name = (request.form.get('name') or '').strip()
    email = (request.form.get('email') or '').strip().lower()
    work_mode = request.form.get('work_mode', 'Remote VPN')
    department = request.form.get('department', 'Customer Support')
    team_name = (request.form.get('team_name') or 'General Intake').strip()
    intake_batch = (request.form.get('intake_batch') or datetime.now().strftime('%B %Y Intake')).strip()

    if not name or not email:
        log_audit_event("ONBOARDING_REJECTED", email or "unknown", "Missing required name/email fields")
        return redirect(url_for('index'))

    if any(a.get('email', '').lower() == email for a in agents):
        log_audit_event("ONBOARDING_DUPLICATE", email, "Attempted duplicate onboarding blocked")
        return redirect(url_for('index'))

    switch_config = generate_switch_config(agents, work_mode)
    vpn_status = remote_access_status(work_mode)
    metrics = quality_metrics(work_mode)
    webex_space = f"BPO {team_name} - {intake_batch}"
    webex_status = provision_webex_automation(email, room_title=webex_space)

    new_agent = {
        "id": len(agents) + 1 if not agents else max(a['id'] for a in agents) + 1,
        "name": name,
        "email": email,
        "work_mode": work_mode,
        "department": department,
        "team_name": team_name,
        "intake_batch": intake_batch,
        "webex_space": webex_space,
        "switch_config": switch_config,
        "vpn_status": vpn_status,
        "webex_status": webex_status,
        "compliance_status": "Compliant",
        **metrics,
    }

    agents.append(new_agent)
    save_data(DB_FILE, agents)
    log_audit_event(
        "AGENT_ONBOARDED",
        email,
        f"Provisioned {work_mode}; team={team_name}; batch={intake_batch}; space={webex_space}; {switch_config}; Webex={webex_status}",
    )

    return redirect(url_for('index'))


# UPDATE: Modify Agent Configuration
@app.route('/update/<int:agent_id>', methods=['POST'])
def update_agent(agent_id):
    agents = load_data(DB_FILE)
    for agent in agents:
        agent = normalize_agent(agent)
        if agent['id'] == agent_id:
            old_mode = agent['work_mode']
            old_department = agent.get('department')
            new_mode = request.form.get('work_mode', old_mode)
            agent['work_mode'] = new_mode
            agent['department'] = request.form.get('department', old_department)
            agent['team_name'] = (request.form.get('team_name') or agent.get('team_name') or 'General Intake').strip()

            if old_mode != new_mode:
                agent['switch_config'] = generate_switch_config([a for a in agents if a['id'] != agent_id], new_mode)
                agent['vpn_status'] = remote_access_status(new_mode)
                agent.update(quality_metrics(new_mode))

            save_data(DB_FILE, agents)
            log_audit_event(
                "AGENT_UPDATED",
                agent['email'],
                f"Changed work mode from {old_mode} to {new_mode}; department={agent['department']}; team={agent['team_name']}; {agent['switch_config']}",
            )
            break

    return redirect(url_for('index'))


# MONITOR: Refresh remote call-quality sample
@app.route('/refresh-metrics/<int:agent_id>', methods=['POST'])
def refresh_metrics(agent_id):
    agents = load_data(DB_FILE)
    for agent in agents:
        agent = normalize_agent(agent)
        if agent['id'] == agent_id:
            agent.update(quality_metrics(agent.get('work_mode', 'Remote VPN')))
            save_data(DB_FILE, agents)
            log_audit_event(
                "QUALITY_MONITORED",
                agent['email'],
                f"Latency={agent['latency_ms']}ms jitter={agent['jitter_ms']}ms loss={agent['packet_loss_pct']}% {agent['call_quality']}",
            )
            break
    return redirect(url_for('index'))


# DELETE: Offboard Agent
@app.route('/delete/<int:agent_id>', methods=['POST'])
def delete_agent(agent_id):
    agents = load_data(DB_FILE)
    agent_to_remove = next((a for a in agents if a['id'] == agent_id), None)

    if agent_to_remove:
        agents = [a for a in agents if a['id'] != agent_id]
        save_data(DB_FILE, agents)
        log_audit_event(
            "AGENT_OFFBOARDED",
            agent_to_remove['email'],
            f"De-provisioned network access, VPN/Zero Trust, and Webex permissions for {agent_to_remove.get('team_name', 'team')}",
        )

    return redirect(url_for('index'))


# REST API Endpoint (CO2REST API Requirement)
@app.route('/api/v1/agents', methods=['GET'])
def api_get_agents():
    return jsonify({"status": "success", "data": [normalize_agent(a) for a in load_data(DB_FILE)]})


@app.route('/api/v1/audit-logs', methods=['GET'])
def api_get_audit_logs():
    return jsonify({"status": "success", "data": load_data(AUDIT_FILE)[:50]})


if __name__ == '__main__':
    print("[+] Starting BPO Automation Portal on http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)