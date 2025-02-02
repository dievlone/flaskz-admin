## 关于

NSO扩展，用于将NSO操作从数据模型中解耦

## 使用

- `apply`用于NSO下发，通过创建继承自`NSOApply`的子类和重写方法实现对不同网络服务的NSO操作
    - 重写`get_url/get_url_params`方法指定请求url及查询参数
    - 重写`to_nso_data`方法返回调用NSO API的payload
    - 除了支持单个NSO业务的操作，还支持通过`yang-patch`对多个业务的批量下发
        - 重写`get_patch_value_key`方法返回yang path value的key ex)srte:sr-policy
        - 重写`get_patch_target`方法返回yang path的target
- `nso_urls.py`中指定NSO请求的URL列表
- `model`用于数据模型类的扩展，`ModelNSOMixin`重写了`before_add/before_update/before_delete`方法为业务模型增加NSO逻辑，可以通过创建继承自ModelNSOMixin的子类和重写方法实现对不同网络服务的NSO操作
    - 重写`get_nso_apply`方法指定对应的apply(解耦)
    - 重写`get_nso_data`方法返回供apply使用的数据，

### apply.to_nso_data和model.get_nso_data的区别

两者都用于返回参数，但是用途不太一样

- **apply.to_nso_data返回的是调用NSO的payload**，一般不建议在其中再进行数据查询等操作
- **model.get_nso_data返回的是供apply使用的数据**，包含apply所需的全部参数，可能需要在现有数据基础上附加一些NSO用到的信息，例如)添加设备时，需要附加ned和授权组相关的信息

## 示例

1. 数据模型类

   ```python
   class Device(ModelBase, ModelNSOMixin, ModelMixin):  # 继承ModelNSOMixin以添加NSO调用功能
       """设备"""
       __tablename__ = 'devices'
   
       id = Column(Integer, primary_key=True, autoincrement=True)
       name = Column(String(32), unique=True, nullable=False)   # 管理名称
       hostname = Column(String(32))    # 主机名
       vendor_id = Column(Integer, ForeignKey("device_vendors.id")) # 厂商
       model_id = Column(Integer, ForeignKey("device_models.id"))   # 设备型号
       ip_address = Column(String(32))  # 地址
       protocol = Column(String(32))    # 管理协议(ssh/telnet)
       port = Column(Integer)   # 管理端口
       auth_id = Column(Integer, ForeignKey("device_auths.id")) # 授权组
   
       @classmethod
       def get_nso_data(cls, json_data, op_type):       # 返回apply需要的全部参数
           auth = DeviceAuth.query_by_pk(json_data.get('auth_id'))
           if auth is None:
               return None
           dev_model = DeviceModel.query_by_pk(json_data.get("model_id"))
           if dev_model is None:
               return None
           json_data['auth'] = {'id': auth.id, 'name': auth.name}
           json_data['ned'] = {'type': dev_model.ned.type, 'name': dev_model.ned.name,
                               'oper_name': dev_model.ned.oper_name}
           return json_data
   
       @classmethod
       def get_nso_apply(cls):      # 指定对应的NSOApply
           return DeviceNSOApply
   ```

2. NSO下发类

    ```python
    class DeviceNSOApply(NSOApply):  # 用于NSO调用
    
        @classmethod
        def to_nso_data(cls, value, op_type):  # 返回调用NSO的payload，value包含payload所需的全部参数
            if op_type == 'delete' or op_type is None:
                return value
    
            ned = value.get('ned', {})
            auth_name = value.get('auth').get('name')
            ned_type = ned.get('type')
            ned_oper_name = ned.get('oper_name')
            ned_id = ned_oper_name or ned.get('name')
            device_type = {
                ned_type: {
                    'ned-id': ned_id,
                }
            }
            if ned_type != 'netconf':
                device_type[ned_type]['protocol'] = value.get('protocol')
    
            response = {
                'name': value.get('name'),
                'address': value.get('ip_address'),
                'port': value.get('port'),
                'authgroup': auth_name,
                'device-type': device_type,
                'state': {
                    'admin-state': 'unlocked'
                }
            }
    
            if ned_oper_name:
                response['live-status-protocol'] = [{
                    'name': '',
                    'authgroup': auth_name,
                    'device-type': device_type
                }
                ]
            return {
                'tailf-ncs:device': [response]
            }
    
        @classmethod
        def get_url(cls, value):  # 指定NSO URL
            return nso_urls.device
    ```