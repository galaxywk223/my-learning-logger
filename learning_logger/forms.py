from flask_wtf import FlaskForm
# MODIFIED: Added FileRequired to the import list
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, BooleanField, SubmitField, RadioField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Optional


from .models import User

class LoginForm(FlaskForm):
    """登录表单"""
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField('记住我')
    submit = SubmitField('登录')

class RegistrationForm(FlaskForm):
    """注册表单"""
    username = StringField('用户名', validators=[DataRequired()])
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('密码', validators=[DataRequired()])
    password2 = PasswordField(
        '确认密码', validators=[DataRequired(), EqualTo('password', message='两次输入的密码必须一致。')])
    submit = SubmitField('注册')

    def validate_username(self, username):
        """验证用户名是否已被使用"""
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('该用户名已被使用，请换一个。')

    def validate_email(self, email):
        """验证邮箱是否已被使用"""
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('该邮箱已被注册，请换一个。')

class DataImportForm(FlaskForm):
    """数据导入表单，包含文件上传和CSRF保护"""
    file = FileField(
        '选择 .zip 备份文件',
        validators=[
            FileRequired(message='请选择一个文件。'),
            FileAllowed(['zip'], message='只能上传 .zip 文件！')
        ]
    )
    submit = SubmitField('导入并覆盖')

# --- Form for Appearance Settings ---
class AppearanceForm(FlaskForm):
    """外观设置表单"""
    # --- 核心修改：在这里添加了更多的主题选项 ---
    theme = RadioField(
        '主题选择',
        choices=[
            ('palette-purple', '默认主题 (宁静紫)'),
            ('palette-green', '活力绿'),
            ('palette-blue', '商务蓝'),
            ('palette-yellow', '暖阳黄'),
            ('palette-red', '热情红')
        ],
        default='palette-purple',
        validators=[DataRequired()]
    )
    background_image = FileField(
        '自定义背景图片',
        validators=[
            Optional(), # This field is optional
            FileAllowed(['jpg', 'jpeg', 'png', 'gif'], '只允许上传图片文件！')
        ]
    )
    remove_background = BooleanField('移除自定义背景')
    submit = SubmitField('保存设置')