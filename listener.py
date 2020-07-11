
from flask import Flask, request, render_template, redirect, jsonify, url_for
import hmac
import hashlib
import subprocess
import os

app = Flask(__name__)  # Standard Flask app

def verify_hmac_hash(data, signature):
    github_secret = bytes(os.environ['GITHUB_SECRET'], 'UTF-8')
    mac = hmac.new(github_secret, msg=data, digestmod=hashlib.sha1)
    return hmac.compare_digest('sha1=' + mac.hexdigest(), signature)

@app.route("/", methods=['POST'])
def github_payload():
    signature = request.headers.get('X-Hub-Signature')
    data = request.data
    if verify_hmac_hash(data, signature):
        if request.headers.get('X-GitHub-Event') == "ping":
            return jsonify({'msg': 'Ok'})
        if request.headers.get('X-GitHub-Event') == "push":
            payload = request.get_json()
            if payload['commits'][0]['distinct'] == True and payload["ref"] == "refs/heads/master":
                try:
                    venv_output = subprocess.check_output(['source', 'venv/bin/activate'],) 
                    cmd_output = subprocess.check_output(
                        ['git', 'pull', 'origin', 'master'],)
                    pip_output = subprocess.check_output(['pip', 'install', '-r', 'requirements.txt'],)
                    return jsonify({'msg': str("pull success and requirements downloaded")})
                except subprocess.CalledProcessError as error:
                    return jsonify({'msg': str(error.output)})
            else:
                return jsonify({'msg': "commit isnt on master or is a duplicate"})

    else:
        return jsonify({'msg': 'invalid hash'})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)