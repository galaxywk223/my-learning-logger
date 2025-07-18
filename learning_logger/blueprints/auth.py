# learning_logger/blueprints/auth.py (MODIFIED TO ADD PRESET MOTTOS)

from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required
from .. import db
# MODIFIED: Import the Motto model
from ..models import User, Motto
from ..forms import LoginForm, RegistrationForm

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # --- Create the user ---
            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()  # Use flush to get the user.id before the final commit

            # --- MODIFICATION: Add preset mottos for the new user ---
            PRESET_MOTTOS = [
                "书山有路勤为径，学海无涯苦作舟。",
                "业精于勤，荒于嬉；行成于思，毁于随。",
                "不积跬步，无以至千里；不积小流，无以成江海。",
                "少壮不努力，老大徒伤悲。",
                "吾生也有涯，而知也无涯。",
                "天行健，君子以自强不息。",
                "明日复明日，明日何其多。我生待明日，万事成蹉跎。"
            ]
            for content in PRESET_MOTTOS:
                motto = Motto(content=content, user_id=user.id)
                db.session.add(motto)

            db.session.commit()  # Commit both the new user and their mottos

            flash('恭喜，您已成功注册！现在可以登录了。', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            # If anything goes wrong, roll back the entire transaction
            db.session.rollback()
            current_app.logger.error(f"Error during registration: {e}")
            flash('注册过程中发生错误，请重试。', 'danger')

    return render_template('register.html', title='注册', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('邮箱或密码无效', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user, remember=form.remember_me.data)
        flash('登录成功！', 'success')

        return redirect(url_for('main.index'))

    return render_template('login.html', title='登录', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功登出。', 'info')
    return redirect(url_for('main.index'))