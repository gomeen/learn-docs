# 7.7.3 IoT 物联网：设备/产品/规则

> 理解 ruoyi IoT 物联网模块的设计。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi IoT 模块的整体设计
- 理解 IoT 设备、产品、规则的关系
- 学会 IoT 设备数据上报
- 能扩展自定义 IoT 业务

## 📚 前置知识

- 21-member-auth.md
- EMQX/MQTT 基础
- WebSocket 基础

## 1. 核心概念

### 1.1 IoT 架构

```
[设备] --(MQTT)--> [IoT 网关] --(HTTP)--> [IoT 平台] --(WebSocket)--> [前端]
                        ↓
                    [设备影子]
                        ↓
                    [规则引擎]
                        ↓
                    [告警通知]
```

### 1.2 ruoyi IoT 子模块

| 子模块 | 说明 |
|--------|------|
| `yudao-module-iot-biz` | IoT 业务实现 |
| `yudao-module-iot-core` | IoT 核心 |
| `yudao-module-iot-gateway` | IoT 网关（设备接入） |

### 1.3 核心概念

| 概念 | 说明 |
|------|------|
| 产品 | 设备类型定义（智能水表） |
| 设备 | 具体设备实例（水表-001） |
| 物模型 | 设备的属性、事件、服务 |
| 设备影子 | 设备状态的虚拟镜像 |
| 规则引擎 | 数据处理规则 |

## 2. 代码示例

### 2.1 设备接入（MQTT）

```java
// IoT 网关接收 MQTT 消息
@PostMapping("/device/upload")
public CommonResult<Boolean> handleDeviceUpload(@RequestBody DeviceUploadReq req) {
    deviceDataService.handleUpload(req);
    return success(true);
}

@Transactional
public void handleUpload(DeviceUploadReq req) {
    // 1. 校验设备
    DeviceDO device = deviceMapper.selectByDeviceKey(req.getDeviceKey());
    // 2. 解析物模型数据
    Map<String, Object> properties = parseProperties(req);
    // 3. 更新设备影子
    deviceShadowService.updateShadow(device.getId(), properties);
    // 4. 触发规则引擎
    ruleEngineService.process(device, properties);
    // 5. 记录日志
    deviceLogService.log(device, req);
}
```

### 2.2 产品定义（物模型）

```json
{
  "properties": [
    {
      "identifier": "temperature",
      "name": "温度",
      "type": "float",
      "specs": {
        "min": "-40",
        "max": "80"
      }
    }
  ],
  "events": [
    {
      "identifier": "highTemperature",
      "name": "高温告警"
    }
  ]
}
```

### 2.3 规则引擎

```java
@EventListener
public void onDevicePropertyChange(DevicePropertyChangeEvent event) {
    // 1. 查询规则
    List<RuleDO> rules = ruleMapper.selectByTriggerEvent("property_change");
    for (RuleDO rule : rules) {
        // 2. 执行规则
        if (evaluateRule(rule, event)) {
            executeAction(rule, event);
        }
    }
}

private boolean evaluateRule(RuleDO rule, DevicePropertyChangeEvent event) {
    // 例如：温度 > 80
    if (rule.getCondition().contains("temperature >")) {
        Double temperature = (Double) event.getProperties().get("temperature");
        return temperature > 80;
    }
    return false;
}
```

## 3. ruoyi 仓库源码解读

### 3.1 IoT 模块结构

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-iot/`

```
yudao-module-iot/
├── yudao-module-iot-biz/      # 业务模块
│   ├── controller/admin/
│   │   ├── product/           # 产品
│   │   ├── device/            # 设备
│   │   └── rule/              # 规则
│   └── service/
├── yudao-module-iot-core/     # 核心（物模型）
└── yudao-module-iot-gateway/  # 网关
```

### 3.2 设备管理

```java
@Tag(name = "管理后台 - IoT 设备")
@RestController
@RequestMapping("/iot/device")
@Validated
public class IotDeviceController {

    @Resource
    private IotDeviceService deviceService;

    @PostMapping("/create")
    public CommonResult<Long> createDevice(@Valid @RequestBody IotDeviceSaveReqVO createReqVO) {
        return success(deviceService.createDevice(createReqVO));
    }

    @GetMapping("/page")
    public CommonResult<PageResult<IotDeviceRespVO>> getDevicePage(@Valid IotDevicePageReqVO pageVO) {
        return success(deviceService.getDevicePage(pageVO));
    }
}
```

## 4. 关键要点总结

- ruoyi IoT 是独立的业务模块
- 通过 MQTT 协议接入设备
- 物模型是设备数据规范
- 设备影子 + 规则引擎处理数据
- WebSocket 推送给前端

## 5. 练习题

### 练习 1：基础（必做）

说明 IoT 三层架构（设备层、网关层、平台层）各自的职责。

### 练习 2：进阶

阅读 `IotDeviceServiceImpl.java`，理解设备的注册流程。

### 练习 3：挑战（选做）

设计"智能家居"场景：温湿度传感器数据每分钟上报，温度 > 30 自动开空调。说明数据流和实现步骤。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-iot/`
- EMQX 文档：https://docs.emqx.io/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
