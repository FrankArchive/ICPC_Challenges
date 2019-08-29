from base64 import b64decode
import json

from flask import Blueprint

from CTFd.models import (
    Challenges, Tags, Hints,
    Fails, Solves,
    Flags, db, ChallengeFiles
)
from CTFd.plugins.challenges import BaseChallenge
from CTFd.utils.uploads import delete_file
from CTFd.utils.user import get_ip
from .api import (
    update_problem,
    prepare_challenge,
    challenge_prepared,
    request_judge
)

cache = {}


class ICPCChallenge(BaseChallenge):
    id = "programming"
    name = "programming"
    route = "/plugins/programming_challenges/assets/"
    templates = {  # Handlebars templates used for each aspect of challenge editing & viewing
        "create": "/plugins/programming_challenges/assets/create.html",
        "update": "/plugins/programming_challenges/assets/update.html",
        "view": "/plugins/programming_challenges/assets/view.html",
    }
    scripts = {  # Scripts that are loaded when a template is loaded
        "create": "/plugins/programming_challenges/assets/create.js",
        "update": "/plugins/programming_challenges/assets/update.js",
        "view": "/plugins/programming_challenges/assets/view.js",
    }
    blueprint = Blueprint(
        "programming_challenges",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )

    @staticmethod
    def create(request):
        data = request.form or request.get_json()
        challenge = ICPCModel(**data)

        db.session.add(challenge)
        db.session.commit()

        return challenge

    @staticmethod
    def read(challenge):
        challenge = ICPCModel.query.filter_by(id=challenge.id).first()
        return {
            "id": challenge.id,
            "name": challenge.name,
            "value": challenge.value,
            "description": challenge.description,
            "category": challenge.category,
            "state": challenge.state,
            "max_attempts": challenge.max_attempts,
            "type": challenge.type,
            "type_data": {
                "id": ICPCChallenge.id,
                "name": ICPCChallenge.name,
                "templates": ICPCChallenge.templates,
                "scripts": ICPCChallenge.scripts,
            },
            'max_cpu_time': challenge.max_cpu_time,
            'max_real_time': challenge.max_real_time,
            'max_memory': challenge.max_memory,
            'max_process_number': challenge.max_process_number,
            'max_output_size': challenge.max_output_size,
            'max_stack': challenge.max_stack,
        }

    @staticmethod
    def update(challenge, request):
        data = request.form or request.get_json()

        for attr, value in data.items():
            if attr in [
                'id', 'name', 'value', 'description', 'category', 'state', 'max_attempts', 'type', 'type_data',

                'max_cpu_time', 'max_real_time', 'max_memory', 'max_process_number', 'max_output_size', 'max_stack'
            ]:
                setattr(challenge, attr, value)
        if challenge.problem_id != -1 and challenge_prepared(challenge.problem_id):
            update_problem(challenge.problem_id, limits={
                i: int(data[i]) for i in
                ['max_cpu_time', 'max_real_time', 'max_memory', 'max_process_number', 'max_output_size', 'max_stack']
            })
        db.session.commit()
        return challenge

    @staticmethod
    def delete(challenge):
        Fails.query.filter_by(challenge_id=challenge.id).delete()
        Solves.query.filter_by(challenge_id=challenge.id).delete()
        Flags.query.filter_by(challenge_id=challenge.id).delete()
        files = ChallengeFiles.query.filter_by(challenge_id=challenge.id).all()
        for f in files:
            delete_file(f.id)
        ChallengeFiles.query.filter_by(challenge_id=challenge.id).delete()
        Tags.query.filter_by(challenge_id=challenge.id).delete()
        Hints.query.filter_by(challenge_id=challenge.id).delete()
        ICPCModel.query.filter_by(id=challenge.id).delete()
        Challenges.query.filter_by(id=challenge.id).delete()
        db.session.commit()

    @staticmethod
    def attempt(challenge, request):
        r = request.form or request.get_json()
        r['code'] = b64decode(r['submission']).decode()
        prepare_challenge(challenge)
        pid = ICPCModel.query.filter(
            ICPCModel.id == challenge.id).first().problem_id
        content = request_judge(pid, r['code'], r['language'])
        cache[r['submission_nonce']] = content
        if content['result'] != 0:
            return False, content['message']
        else:
            return True, 'Accepted'

    @staticmethod
    def fail(user, team, challenge, request):
        data = request.form or request.get_json()
        db.session.add(Fails(
            user_id=user.id,
            team_id=team.id if team else None,
            challenge_id=challenge.id,
            ip=get_ip(request),
            provided=json.dumps(cache[data['submission_nonce']])
        ))
        cache.pop(data['submission_nonce'])
        db.session.commit()
        db.session.close()

    @staticmethod
    def solve(user, team, challenge, request):
        data = request.form or request.get_json()
        db.session.add(Solves(
            user_id=user.id,
            team_id=team.id if team else None,
            challenge_id=challenge.id,
            ip=get_ip(request),
            provided=json.dumps(cache[data['submission_nonce']])
        ))
        cache.pop(data['submission_nonce'])
        db.session.commit()
        db.session.close()


class ICPCModel(Challenges):  # db
    __mapper_args__ = {"polymorphic_identity": "programming"}
    id = db.Column(None, db.ForeignKey("challenges.id"), primary_key=True)

    problem_id = db.Column(db.Integer, default=-1)  # 指在评测端的id

    max_cpu_time = db.Column(db.Integer, default=1000)
    max_real_time = db.Column(db.Integer, default=-1)
    max_memory = db.Column(db.Integer, default=32 * 1024 * 1024)
    max_process_number = db.Column(db.Integer, default=200)
    max_output_size = db.Column(db.Integer, default=10000)
    max_stack = db.Column(db.Integer, default=32 * 1024 * 1024)

    def __init__(self, *args, **kwargs):
        super(ICPCModel, self).__init__(**kwargs)
        self.initial = kwargs["value"]


# Better seperate from CTFd File model
# for no one want's contestants to access the test cases
class JudgeCaseFiles(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'))
    location = db.Column(db.Text)

    def __init__(self, challenge_id, location):
        self.challenge_id = challenge_id
        self.location = location