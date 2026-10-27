from datetime import datetime
from enum import Enum
from typing import List, Callable, Iterable
import unittest

# --- 1. Enums ---
class DeviceStatus(Enum):
    Available = 1
    Borrowed = 2
    UnderMaintenance = 3

class AlertSeverity(Enum):
    Information = 1
    Warning = 2
    Critical = 3

# --- 2. EventArgs & Exceptions ---
class DeviceStatusChangedEventArgs:
    def __init__(self, device_id: str, old_status: DeviceStatus, new_status: DeviceStatus, changed_at: datetime):
        self.device_id = device_id
        self.old_status = old_status
        self.new_status = new_status
        self.changed_at = changed_at

class DeviceAlertEventArgs:
    def __init__(self, device_id: str, message: str, severity: AlertSeverity, occurred_at: datetime):
        self.device_id = device_id
        self.message = message
        self.severity = severity
        self.occurred_at = occurred_at

class InvalidDeviceReadingException(Exception):
    def __init__(self, device_id: str, invalid_value: int, message: str = ""):
        super().__init__(message or f"Giá trị đọc không hợp lệ {invalid_value} cho thiết bị {device_id}")
        self.device_id = device_id
        self.invalid_value = invalid_value

# --- 3. Abstract Publisher: TeachingDevice ---
class TeachingDevice:
    def __init__(self, device_id: str, name: str):
        self.id = device_id
        self.name = name
        self._status = DeviceStatus.Available
        self.status_changed: List[Callable[[object, DeviceStatusChangedEventArgs], None]] = []
        self.alert_raised: List[Callable[[object, DeviceAlertEventArgs], None]] = []

    @property
    def status(self) -> DeviceStatus:
        return self._status

    def change_status(self, new_status: DeviceStatus):
        if self._status == new_status:
            return
        old_status = self._status
        self._status = new_status
        self.on_status_changed(DeviceStatusChangedEventArgs(self.id, old_status, new_status, datetime.now()))

    def raise_alert(self, message: str, severity: AlertSeverity):
        self.on_alert_raised(DeviceAlertEventArgs(self.id, message, severity, datetime.now()))

    def on_status_changed(self, e: DeviceStatusChangedEventArgs):
        for handler in self.status_changed:
            handler(self, e)

    def on_alert_raised(self, e: DeviceAlertEventArgs):
        for handler in self.alert_raised:
            handler(self, e)

# --- 4. Concrete Devices ---
class ProjectorRemote(TeachingDevice):
    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name)
        self._battery_level = 100

    @property
    def battery_level(self) -> int:
        return self._battery_level

    def update_battery_level(self, new_level: int):
        if not (0 <= new_level <= 100):
            raise InvalidDeviceReadingException(self.id, new_level)
        
        old_level = self._battery_level
        self._battery_level = new_level

        if old_level >= 20 and new_level == 0:
            self.raise_alert("Pin đã cạn hoàn toàn", AlertSeverity.Critical)
        elif old_level >= 20 and new_level < 20:
            self.raise_alert(f"Mức pin thấp: {new_level}%", AlertSeverity.Warning)
        elif old_level > 0 and new_level == 0:
            self.raise_alert("Pin đã cạn hoàn toàn", AlertSeverity.Critical)

class AirConditionerRemote(TeachingDevice):
    def __init__(self, device_id: str, name: str, assigned_room: str):
        super().__init__(device_id, name)
        self.assigned_room = assigned_room
        self._is_responsive = True

    @property
    def is_responsive(self) -> bool:
        return self._is_responsive

    def update_response_state(self, is_responsive: bool):
        old_state = self._is_responsive
        self._is_responsive = is_responsive

        if old_state and not is_responsive:
            self.raise_alert("Điều hòa mất kết nối/không phản hồi", AlertSeverity.Critical)

class WirelessMicrophone(TeachingDevice):
    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name)
        self._battery_level = 100
        self._signal_quality = 100

    @property
    def battery_level(self) -> int:
        return self._battery_level

    @property
    def signal_quality(self) -> int:
        return self._signal_quality

    def update_battery_level(self, new_level: int):
        if not (0 <= new_level <= 100):
            raise InvalidDeviceReadingException(self.id, new_level)
        old_level = self._battery_level
        self._battery_level = new_level

        if new_level == 0:
            self.raise_alert("Pin Micro bằng 0%", AlertSeverity.Critical)
        elif old_level >= 30 and new_level < 30:
            self.raise_alert(f"Pin Micro yếu: {new_level}%", AlertSeverity.Warning)

    def update_signal_quality(self, new_quality: int):
        if not (0 <= new_quality <= 100):
            raise InvalidDeviceReadingException(self.id, new_quality)
        old_quality = self._signal_quality
        self._signal_quality = new_quality

        if new_quality == 0:
            self.raise_alert("Chất lượng tín hiệu Micro bằng 0%", AlertSeverity.Critical)
        elif old_quality >= 40 and new_quality < 40:
            self.raise_alert(f"Chất lượng tín hiệu Micro kém: {new_quality}%", AlertSeverity.Warning)

# --- 5. Subscribers ---
class ConsoleNotificationService:
    def handle_alert(self, sender, e: DeviceAlertEventArgs):
        print(f"   [THÔNG BÁO] [{e.severity.name}] Thiết bị {e.device_id}: {e.message}")

class DeviceAuditLogger:
    def __init__(self):
        self._entries = []

    @property
    def entries(self):
        return self._entries

    def handle_status_changed(self, sender, e: DeviceStatusChangedEventArgs):
        log_msg = f"{e.changed_at.strftime('%H:%M:%S')}: {e.device_id}, {e.old_status.name} -> {e.new_status.name}"
        self._entries.append(log_msg)
        print(f"   [AUDIT LOG] {log_msg}")

class MaintenanceService:
    def __init__(self):
        self._requests = []

    @property
    def requests(self):
        return self._requests

    def handle_critical_alert(self, sender, e: DeviceAlertEventArgs):
        if e.severity != AlertSeverity.Critical:
            return
        req_msg = f"Yêu cầu bảo trì cho {e.device_id}: {e.message}"
        self._requests.append(req_msg)
        print(f"   [BẢO TRÌ] 🚨 {req_msg}")

# --- 6. Coordinator ---
class DeviceMonitoringCoordinator:
    def __init__(self, devices: Iterable[TeachingDevice], notification_service: ConsoleNotificationService, audit_logger: DeviceAuditLogger, maintenance_service: MaintenanceService):
        self.devices = list(devices)
        self.notification_service = notification_service
        self.audit_logger = audit_logger
        self.maintenance_service = maintenance_service
        self._subscribed = False

    def subscribe(self):
        if self._subscribed:
            return
        for device in self.devices:
            if self.notification_service.handle_alert not in device.alert_raised:
                device.alert_raised.append(self.notification_service.handle_alert)
            if self.maintenance_service.handle_critical_alert not in device.alert_raised:
                device.alert_raised.append(self.maintenance_service.handle_critical_alert)
            if self.audit_logger.handle_status_changed not in device.status_changed:
                device.status_changed.append(self.audit_logger.handle_status_changed)
        self._subscribed = True

    def unsubscribe(self):
        if not self._subscribed:
            return
        for device in self.devices:
            if self.notification_service.handle_alert in device.alert_raised:
                device.alert_raised.remove(self.notification_service.handle_alert)
            if self.maintenance_service.handle_critical_alert in device.alert_raised:
                device.alert_raised.remove(self.maintenance_service.handle_critical_alert)
            if self.audit_logger.handle_status_changed in device.status_changed:
                device.status_changed.remove(self.audit_logger.handle_status_changed)
        self._subscribed = False

    def dispose(self):
        self.unsubscribe()


# --- 7. Các trường hợp kiểm thử (Test Cases) ---
class TestDeviceMonitoringSystem(unittest.TestCase):

    def test_case_1_status_change_and_logging(self):
        print("\n--- CHẠY TEST CASE 1: Kiểm tra thay đổi trạng thái & Nhật ký (Audit Logger) ---")
        projector = ProjectorRemote("PROJ-101", "Máy chiếu Sony phòng 401")
        logger = DeviceAuditLogger()
        projector.status_changed.append(logger.handle_status_changed)

        # Thay đổi trạng thái
        projector.change_status(DeviceStatus.Borrowed)
        projector.change_status(DeviceStatus.UnderMaintenance)

        # Kiểm tra kết quả
        self.assertEqual(len(logger.entries), 2)
        self.assertIn("Available -> Borrowed", logger.entries[0])
        self.assertIn("Borrowed -> UnderMaintenance", logger.entries[1])
        print("=> Test Case 1 thành công!")

    def test_case_2_critical_alert_and_maintenance(self):
        print("\n--- CHẠY TEST CASE 2: Kiểm tra cảnh báo Critical kích hoạt MaintenanceService ---")
        ac = AirConditionerRemote("AC-202", "Điều hòa Panasonic", "Phòng 502")
        maintenance = MaintenanceService()
        notification = ConsoleNotificationService()

        # Đăng ký sự kiện
        ac.alert_raised.append(notification.handle_alert)
        ac.alert_raised.append(maintenance.handle_critical_alert)

        # Giả lập điều hòa chuyển sang mất phản hồi (gây lỗi Critical)
        ac.update_response_state(False)

        # Kiểm tra xem MaintenanceService có tự động tạo yêu cầu bảo trì không
        self.assertEqual(len(maintenance.requests), 1)
        self.assertIn("AC-202", maintenance.requests[0])
        print("=> Test Case 2 thành công!")

    def test_case_3_invalid_reading_exception(self):
        print("\n--- CHẠY TEST CASE 3: Kiểm tra ngoại lệ InvalidDeviceReadingException (Pin ngoài 0-100) ---")
        mic = WirelessMicrophone("MIC-303", "Micro không dây Shure")

        # Cố gắng truyền giá trị pin không hợp lệ (> 100)
        with self.assertRaises(InvalidDeviceReadingException) as context:
            mic.update_battery_level(120)

        print(f"   [Ngoại lệ bắt được đúng ý đồ]: {context.exception}")
        self.assertEqual(context.exception.device_id, "MIC-303")
        self.assertEqual(context.exception.invalid_value, 120)
        print("=> Test Case 3 thành công!")


if __name__ == '__main__':
    unittest.main()