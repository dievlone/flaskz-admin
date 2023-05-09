from flask import Flask, session
from flaskz import log, models
from flaskz.utils import init_app_config

from config import config
from . import sys_mgmt, main, api, sys_init
from .sys_mgmt import auth


def create_app(config_name):
    app = Flask(__name__)
    # app.url_map.strict_slashes = False  # 不需重定向而直接使用斜杠视图路由 ex)'user' and 'user/'

    # 配置
    config_name = config_name.lower()
    app_config = config[config_name]
    app.config.from_object(app_config)
    # 跨域支持, pip install flask-cors
    # CORS(app)

    # 初始化
    app_config.init_app(app)
    init_app_config(app_config)  # 初始化系统配置, 方便使用get_app_config获取应用配置
    sys_init.init_app(None)  # 系统初始化，中文message等
    log.init_log(app)  # 初始化日志
    log.flaskz_logger.info('-- start application with %s config --' % config_name)
    models.init_model(app)  # 初始化数据库

    # 系统管理
    _init_login(app)
    _init_model_rest(app)
    # _init_license(app)

    # 注册API
    main.init_app(app)
    app.register_blueprint(main.main_bp, url_prefix='/')
    app.register_blueprint(api.api_bp, url_prefix='/api/v1.0')
    app.register_blueprint(sys_mgmt.sys_mgmt_bp, url_prefix='/sys-mgmt')

    @app.before_request
    def before_request():
        # refresh session life time and update client cookie(Flask's sessions are client-side sessions)
        # if use session to store user information, please set it before every request.
        session.permanent = True

    return app


def _init_login(app):
    """初始化login模块，按需使用"""
    from flask_login import LoginManager
    login_manager = LoginManager()
    # 用户加载回调函数，可以通过id查找对应的用户
    login_manager.user_loader(auth.load_user_by_id)
    # 根据request校验用户，支持Token和Basic Auth
    login_manager.request_loader(auth.load_user_by_request)
    # 初始化flask应用的用户登录管理
    login_manager.init_app(app)


def _init_model_rest(app):
    """初始化model rest api权限控制和操作日志记录，按需使用"""
    from flaskz.rest import ModelRestManager
    model_rest_manager = ModelRestManager()
    # check current user login or not
    model_rest_manager.login_check(auth.login_check)
    # 检查用户是否有菜单&操作权限
    model_rest_manager.permission_check(auth.permission_check)
    # 日志记录函数
    model_rest_manager.logging(sys_mgmt.log_operation)
    model_rest_manager.init_app(app)


def _init_license(app):
    """
    初始化license模块，按需使用
    pip install pycryptodome

    请确保有公钥文件和上传License
    公钥文件: APP_LICENSE_PUBLIC_KEY_FILEPATH = './_license/public.key'
    License菜单path: APP_LICENSE_MENU_PATH = 'licenses' # 参考sys_mgmt/router.sys_auth_account_query()
    """
    # from .sys_mgmt import license
    # *在sys_mgmt.router中导入license路由from .license import router，否则alembic不能发现License模型类*
    #
    # license_manager = license.LicenseManager()
    # license_manager.load_license(license.load_license)  # load license callback
    # license_manager.request_check(license.request_check_by_license)  # request check callback
    # license_manager.init_app(app)
    pass
