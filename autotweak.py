#!/usr/bin/env python3
# and yeah.. my first script in spanish
# if you want a English version, feedback.

"""
AutoTweak - Optimizador de rendimiento para Linux
Un script que detecta y aplica automáticamente optimizaciones 
para mejorar el rendimiento de distribuciones Linux.
"""

import os
import sys
import subprocess
import shutil
import time
import json
import argparse
import logging
import datetime
import platform
import re
from pathlib import Path

# Configuración de logging
log_dir = "/var/log/autotweak"
if not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir)
    except PermissionError:
        log_dir = os.path.expanduser("~/.autotweak")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

log_file = os.path.join(log_dir, f"autotweak_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("autotweak")

# Archivo para almacenar cambios y permitir revertirlos
CHANGES_FILE = os.path.join(log_dir, "autotweak_changes.json")

class Colors:
    """Colores para la terminal"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_banner():
    """Muestra el banner del programa"""
    banner = f"""
    {Colors.BLUE}{Colors.BOLD}
    ╔═══════════════════════════════════════════════════════════════════════════════════╗
    ║                                                                                   ║
    ║   █████╗ ██╗   ██╗████████╗ ██████╗ ████████╗██╗    ██╗███████╗ █████╗ ██╗  ██╗   ║
    ║  ██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗╚══██╔══╝██║    ██║██╔════╝██╔══██╗██║ ██╔╝   ║
    ║  ███████║██║   ██║   ██║   ██║   ██║   ██║   ██║ █╗ ██║█████╗  ███████║█████╔╝    ║
    ║  ██╔══██║██║   ██║   ██║   ██║   ██║   ██║   ██║███╗██║██╔══╝  ██╔══██║██╔═██╗    ║
    ║  ██║  ██║╚██████╔╝   ██║   ╚██████╔╝   ██║   ╚███╔███╔╝███████╗██║  ██║██║  ██╗   ║
    ║  ╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝    ╚═╝    ╚══╝╚══╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝   ║
    ║                                                                                   ║
    ║      Optimizador de Rendimiento para Linux v1.0       by Rip70022/craxterpy       ║
    ║         (G) https://www.github.com/Rip70022                                       ║
    ║                                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════════════════════╝
    {Colors.ENDC}
    """
    print(banner)

def check_root():
    """Verifica si el script se ejecuta como root"""
    if os.geteuid() != 0:
        logger.error("Este script debe ejecutarse como root para aplicar la mayoría de las optimizaciones.")
        print(f"{Colors.FAIL}Este script debe ejecutarse como root para aplicar la mayoría de las optimizaciones.{Colors.ENDC}")
        print(f"{Colors.WARNING}Ejecuta: sudo {sys.argv[0]}{Colors.ENDC}")
        sys.exit(1)

def detect_distro():
    """Detecta la distribución Linux"""
    if os.path.exists("/etc/os-release"):
        with open("/etc/os-release", "r") as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("ID="):
                    distro_id = line.split("=")[1].strip().strip('"')
                    if "debian" in distro_id or "ubuntu" in distro_id or "mint" in distro_id:
                        return "debian"
                    elif "arch" in distro_id or "manjaro" in distro_id:
                        return "arch"
                    elif "fedora" in distro_id or "rhel" in distro_id or "centos" in distro_id:
                        return "fedora"
    
    # Intentar detectar usando comandos
    try:
        if shutil.which("apt"):
            return "debian"
        elif shutil.which("pacman"):
            return "arch"
        elif shutil.which("dnf") or shutil.which("yum"):
            return "fedora"
    except:
        pass
    
    return "unknown"

def run_command(command, shell=False):
    """Ejecuta un comando y registra su salida"""
    logger.info(f"Ejecutando: {command}")
    try:
        if shell:
            process = subprocess.run(command, shell=True, check=True, text=True, 
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            process = subprocess.run(command.split(), check=True, text=True, 
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"Comando exitoso: {command}")
        return True, process.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Error al ejecutar {command}: {e.stderr}")
        return False, e.stderr

def save_backup(file_path):
    """Crea una copia de seguridad de un archivo"""
    if os.path.exists(file_path):
        backup_path = f"{file_path}.autotweak.bak"
        shutil.copy2(file_path, backup_path)
        logger.info(f"Backup creado: {backup_path}")
        return backup_path
    return None

def save_changes(changes):
    """Guarda los cambios realizados para poder revertirlos"""
    if os.path.exists(CHANGES_FILE):
        with open(CHANGES_FILE, 'r') as f:
            try:
                existing_changes = json.load(f)
            except json.JSONDecodeError:
                existing_changes = []
    else:
        existing_changes = []
    
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    changes['timestamp'] = timestamp
    existing_changes.append(changes)
    
    with open(CHANGES_FILE, 'w') as f:
        json.dump(existing_changes, f, indent=4)

def clean_system(distro):
    """Limpia el sistema: paquetes innecesarios, cachés y archivos temporales"""
    print(f"\n{Colors.BOLD}🧹 Limpiando el sistema...{Colors.ENDC}")
    changes = {"type": "cleanup", "actions": []}
    
    # Limpiar la caché de paquetes según la distribución
    if distro == "debian":
        success, output = run_command("apt-get clean")
        if success:
            changes["actions"].append("apt-get clean")
        
        success, output = run_command("apt-get autoremove -y")
        if success:
            changes["actions"].append("apt-get autoremove")
    
    elif distro == "arch":
        success, output = run_command("pacman -Sc --noconfirm")
        if success:
            changes["actions"].append("pacman cache clean")
            
        # Eliminar paquetes huérfanos
        success, output = run_command("pacman -Qtdq | pacman -Rns - --noconfirm", shell=True)
        if success and "error" not in output.lower():
            changes["actions"].append("removed orphaned packages")
    
    elif distro == "fedora":
        success, output = run_command("dnf clean all")
        if success:
            changes["actions"].append("dnf clean all")
            
        success, output = run_command("dnf autoremove -y")
        if success:
            changes["actions"].append("dnf autoremove")
    
    # Limpiar archivos temporales
    temp_dirs = ["/tmp", "/var/tmp"]
    for temp_dir in temp_dirs:
        # Excluir archivos esenciales y limpiar solo archivos más antiguos que 1 día
        success, output = run_command(f"find {temp_dir} -type f -atime +1 -delete 2>/dev/null || true", shell=True)
        if success:
            changes["actions"].append(f"cleaned {temp_dir}")
    
    # Limpiar journalctl logs
    success, output = run_command("journalctl --vacuum-time=7d")
    if success:
        changes["actions"].append("cleared old journalctl logs")
    
    # Limpiar cachés de thumbnails
    thumbnail_dirs = [
        os.path.expanduser("~/.cache/thumbnails"),
        os.path.expanduser("~/.thumbnails")
    ]
    
    for thumb_dir in thumbnail_dirs:
        if os.path.exists(thumb_dir):
            success, output = run_command(f"rm -rf {thumb_dir}/*")
            if success:
                changes["actions"].append(f"cleared {thumb_dir}")
    
    save_changes(changes)
    print(f"{Colors.GREEN}✓ Limpieza del sistema completada{Colors.ENDC}")
    return changes

def optimize_ram_swap():
    """Optimiza la RAM y configuración de SWAP"""
    print(f"\n{Colors.BOLD}💾 Optimizando RAM y SWAP...{Colors.ENDC}")
    changes = {"type": "ram_swap", "actions": [], "original_values": {}}
    
    # Verificar si existe swap
    swap_exists = False
    success, output = run_command("swapon --show")
    if success and output.strip():
        swap_exists = True
    
    # Ajustar swappiness
    if swap_exists:
        # Guardar valor original de swappiness
        success, original_swappiness = run_command("cat /proc/sys/vm/swappiness")
        if success:
            changes["original_values"]["swappiness"] = original_swappiness.strip()
        
        # Establecer valor óptimo de swappiness (menor valor = menos uso de swap)
        swappiness_value = "10"  # Valor recomendado para sistemas con buena RAM
        success, output = run_command(f"sysctl -w vm.swappiness={swappiness_value}")
        if success:
            changes["actions"].append(f"set vm.swappiness={swappiness_value}")
            
            # Hacer el cambio permanente
            sysctl_conf = "/etc/sysctl.conf"
            backup_path = save_backup(sysctl_conf)
            if backup_path:
                changes["original_files"] = {sysctl_conf: backup_path}
            
            # Comprobar si la línea ya existe y modificarla o añadirla
            swappiness_line = f"vm.swappiness={swappiness_value}"
            with open(sysctl_conf, "r") as f:
                lines = f.readlines()
            
            new_lines = []
            swappiness_exists = False
            for line in lines:
                if "vm.swappiness" in line and not line.strip().startswith("#"):
                    new_lines.append(f"{swappiness_line}\n")
                    swappiness_exists = True
                else:
                    new_lines.append(line)
            
            if not swappiness_exists:
                new_lines.append(f"{swappiness_line}\n")
            
            with open(sysctl_conf, "w") as f:
                f.writelines(new_lines)
    
    # Optimizar la caché de escritura
    success, original_dirty_ratio = run_command("cat /proc/sys/vm/dirty_ratio")
    if success:
        changes["original_values"]["dirty_ratio"] = original_dirty_ratio.strip()
    
    success, original_dirty_background_ratio = run_command("cat /proc/sys/vm/dirty_background_ratio")
    if success:
        changes["original_values"]["dirty_background_ratio"] = original_dirty_background_ratio.strip()
    
    # Configurar valores optimizados
    success, output = run_command("sysctl -w vm.dirty_ratio=10")
    if success:
        changes["actions"].append("set vm.dirty_ratio=10")
    
    success, output = run_command("sysctl -w vm.dirty_background_ratio=5")
    if success:
        changes["actions"].append("set vm.dirty_background_ratio=5")
    
    # Actualizar en sysctl.conf para que sea permanente
    sysctl_conf = "/etc/sysctl.conf"
    with open(sysctl_conf, "r") as f:
        lines = f.readlines()
    
    dirty_ratio_exists = False
    dirty_bg_ratio_exists = False
    new_lines = []
    
    for line in lines:
        if "vm.dirty_ratio" in line and not line.strip().startswith("#"):
            new_lines.append("vm.dirty_ratio=10\n")
            dirty_ratio_exists = True
        elif "vm.dirty_background_ratio" in line and not line.strip().startswith("#"):
            new_lines.append("vm.dirty_background_ratio=5\n")
            dirty_bg_ratio_exists = True
        else:
            new_lines.append(line)
    
    if not dirty_ratio_exists:
        new_lines.append("vm.dirty_ratio=10\n")
    if not dirty_bg_ratio_exists:
        new_lines.append("vm.dirty_background_ratio=5\n")
    
    with open(sysctl_conf, "w") as f:
        f.writelines(new_lines)
    
    # Activar AutoNUMA si está disponible
    if os.path.exists("/proc/sys/kernel/numa_balancing"):
        success, original_numa = run_command("cat /proc/sys/kernel/numa_balancing")
        if success:
            changes["original_values"]["numa_balancing"] = original_numa.strip()
            success, output = run_command("sysctl -w kernel.numa_balancing=1")
            if success:
                changes["actions"].append("enabled AutoNUMA balancing")
    
    # Instalar earlyoom para gestión de memoria crítica si está disponible
    distro = detect_distro()
    if distro == "debian":
        success, output = run_command("apt-get install -y earlyoom")
        if success:
            changes["actions"].append("installed earlyoom")
            run_command("systemctl enable --now earlyoom")
    elif distro == "arch":
        success, output = run_command("pacman -S --noconfirm earlyoom")
        if success:
            changes["actions"].append("installed earlyoom")
            run_command("systemctl enable --now earlyoom")
    elif distro == "fedora":
        success, output = run_command("dnf install -y earlyoom")
        if success:
            changes["actions"].append("installed earlyoom")
            run_command("systemctl enable --now earlyoom")
    
    save_changes(changes)
    print(f"{Colors.GREEN}✓ Optimización de RAM y SWAP completada{Colors.ENDC}")
    return changes

def optimize_boot():
    """Optimiza el tiempo de arranque deshabilitando servicios innecesarios"""
    print(f"\n{Colors.BOLD}🚀 Optimizando el arranque del sistema...{Colors.ENDC}")
    changes = {"type": "boot", "actions": [], "disabled_services": []}
    
    # Lista de servicios que podrían ser deshabilitados si no son necesarios
    # NOTA: Estos son ejemplos y deben ser adaptados según el uso del sistema
    potentially_unnecessary_services = [
        "bluetooth.service",        # Si no se usa bluetooth
        "cups.service",             # Si no se usa impresora
        "avahi-daemon.service",     # Si no se necesita descubrimiento de servicios
        "ModemManager.service",     # Si no se usa módem
        "nfs-server.service",       # Si no se comparten archivos NFS
        "saned.service",            # Si no se usa escáner
    ]
    
    # Verificar si podemos usar systemd
    if not os.path.exists("/bin/systemctl") and not os.path.exists("/usr/bin/systemctl"):
        logger.warning("No se encontró systemctl. Esta optimización requiere systemd.")
        print(f"{Colors.WARNING}No se encontró systemctl. La optimización de arranque requiere systemd.{Colors.ENDC}")
        return changes
    
    # Verificar qué servicios están activos y si se pueden deshabilitar
    for service in potentially_unnecessary_services:
        # Verificar si el servicio existe
        success, output = run_command(f"systemctl list-unit-files {service}")
        if not success or "0 unit files listed" in output:
            continue
        
        # Verificar si el servicio está activo
        success, output = run_command(f"systemctl is-active {service}")
        if success and "active" in output:
            # Preguntar al usuario antes de deshabilitar
            print(f"\n{Colors.WARNING}El servicio {service} está activo.{Colors.ENDC}")
            choice = input(f"¿Desactivar {service}? Se recomienda si no utilizas su funcionalidad. [s/N]: ")
            
            if choice.lower() == "s":
                success, output = run_command(f"systemctl disable {service}")
                if success:
                    changes["disabled_services"].append(service)
                    print(f"{Colors.GREEN}✓ Servicio {service} deshabilitado{Colors.ENDC}")
                    changes["actions"].append(f"disabled {service}")
    
    # Reducir el tiempo de espera de TimeoutStartSec y TimeoutStopSec en systemd
    systemd_conf = "/etc/systemd/system.conf"
    backup_path = save_backup(systemd_conf)
    if backup_path:
        if "original_files" not in changes:
            changes["original_files"] = {}
        changes["original_files"][systemd_conf] = backup_path
    
    with open(systemd_conf, "r") as f:
        lines = f.readlines()
    
    new_lines = []
    timeout_start_exists = False
    timeout_stop_exists = False
    
    for line in lines:
        if "TimeoutStartSec" in line and not line.strip().startswith("#"):
            new_lines.append("TimeoutStartSec=15s\n")
            timeout_start_exists = True
        elif "TimeoutStopSec" in line and not line.strip().startswith("#"):
            new_lines.append("TimeoutStopSec=15s\n")
            timeout_stop_exists = True
        else:
            new_lines.append(line)
    
    if not timeout_start_exists:
        new_lines.append("TimeoutStartSec=15s\n")
    if not timeout_stop_exists:
        new_lines.append("TimeoutStopSec=15s\n")
    
    with open(systemd_conf, "w") as f:
        f.writelines(new_lines)
    
    changes["actions"].append("reduced systemd timeout values")
    
    # Optimizar la configuración de Grub
    grub_config = "/etc/default/grub"
    if os.path.exists(grub_config):
        backup_path = save_backup(grub_config)
        if backup_path:
            if "original_files" not in changes:
                changes["original_files"] = {}
            changes["original_files"][grub_config] = backup_path
        
        with open(grub_config, "r") as f:
            lines = f.readlines()
        
        new_lines = []
        cmdline_exists = False
        
        for line in lines:
            if line.startswith("GRUB_CMDLINE_LINUX_DEFAULT="):
                # Añadir parámetros de arranque rápido
                cmdline = line.strip().rstrip('"')
                if cmdline.endswith('"'):
                    cmdline = cmdline[:-1]
                cmdline += " quiet splash fastboot noatime "
                cmdline += 'rootfstype=ext4 "' if 'rootfstype' not in cmdline else '"'
                new_lines.append(cmdline + "\n")
                cmdline_exists = True
                changes["actions"].append("optimized grub command line parameters")
            elif line.startswith("GRUB_TIMEOUT="):
                # Reducir el tiempo de espera de Grub
                new_lines.append("GRUB_TIMEOUT=1\n")
                changes["actions"].append("reduced grub timeout to 1 second")
            else:
                new_lines.append(line)
        
        if not cmdline_exists:
            new_lines.append('GRUB_CMDLINE_LINUX_DEFAULT="quiet splash fastboot noatime rootfstype=ext4"\n')
        
        with open(grub_config, "w") as f:
            f.writelines(new_lines)
        
        # Actualizar grub
        distro = detect_distro()
        if distro == "debian":
            run_command("update-grub")
        elif distro == "arch":
            run_command("grub-mkconfig -o /boot/grub/grub.cfg")
        elif distro == "fedora":
            run_command("grub2-mkconfig -o /boot/grub2/grub.cfg")
    
    # Habilitar fstrim.timer para SSD si existe
    success, output = run_command("systemctl enable fstrim.timer")
    if success:
        changes["actions"].append("enabled periodic TRIM for SSD")
    
    save_changes(changes)
    print(f"{Colors.GREEN}✓ Optimización de arranque completada{Colors.ENDC}")
    return changes

def optimize_kernel():
    """Optimiza los parámetros del kernel para mejorar el rendimiento"""
    print(f"\n{Colors.BOLD}⚙️ Optimizando parámetros del kernel...{Colors.ENDC}")
    changes = {"type": "kernel", "actions": [], "original_values": {}}
    
    sysctl_conf = "/etc/sysctl.conf"
    backup_path = save_backup(sysctl_conf)
    if backup_path:
        changes["original_files"] = {sysctl_conf: backup_path}
    
    # Parámetros a optimizar
    optimizations = [
        # I/O y virtualización de memoria
        ("vm.vfs_cache_pressure", "50", "Reduce la presión sobre la caché VFS"),
        ("vm.dirty_writeback_centisecs", "1500", "Extiende el tiempo entre escrituras a disco"),
        
        # Red
        ("net.core.netdev_max_backlog", "16384", "Aumenta el backlog de interfaces de red"),
        ("net.core.somaxconn", "8192", "Aumenta las conexiones en espera"),
        ("net.ipv4.tcp_fastopen", "3", "Habilita TCP Fast Open"),
        ("net.ipv4.tcp_max_syn_backlog", "8192", "Aumenta las conexiones SYN en espera"),
        ("net.ipv4.tcp_max_tw_buckets", "2000000", "Aumenta el límite de sockets TIME-WAIT"),
        
        # Rendimiento general
        ("kernel.nmi_watchdog", "0", "Desactiva NMI watchdog para ahorro de energía"),
        ("kernel.sched_autogroup_enabled", "1", "Mejora la programación de tareas")
    ]
    
    # Leer el archivo actual
    with open(sysctl_conf, "r") as f:
        current_content = f.read()
    
    # Aplicar optimizaciones
    with open(sysctl_conf, "a") as f:
        f.write("\n# Optimizaciones añadidas por AutoTweak\n")
        
        for param, value, description in optimizations:
            # Verificar si el parámetro ya existe en el archivo
            regex = re.compile(f"^{param.replace('.', '\\.')}\\s*=", re.MULTILINE)
            if regex.search(current_content):
                # Si existe, obtenemos el valor actual
                success, original_value = run_command(f"sysctl -n {param}")
                if success:
                    changes["original_values"][param] = original_value.strip()
                    
                # Actualizamos con el nuevo valor usando sysctl
                success, output = run_command(f"sysctl -w {param}={value}")
                if success:
                    changes["actions"].append(f"updated {param}={value}")
                
                # No lo añadimos al archivo porque ya existe
                continue
            
            # Guardar valor original
            success, original_value = run_command(f"sysctl -n {param}")
            if success:
                changes["original_values"][param] = original_value.strip()
            
            # Aplicar nuevo valor
            success, output = run_command(f"sysctl -w {param}={value}")
            if success:
                changes["actions"].append(f"set {param}={value}")
                f.write(f"# {description}\n{param}={value}\n\n")
    
    # Optimizar el scheduler de I/O si hay discos
    disks = []
    success, output = run_command("lsblk -d -o NAME -n")
    if success:
        disks = [disk.strip() for disk in output.split('\n') if disk.strip()]
    
    # Detectar si hay SSDs
    ssds = []
    for disk in disks:
        if not disk.startswith("loop"):
            success, output = run_command(f"cat /sys/block/{disk}/queue/rotational")
            if success and output.strip() == "0":
                ssds.append(disk)
    
    # Aplicar scheduler óptimo según el tipo de disco
    for disk in disks:
        if not disk.startswith("loop"):
            scheduler_path = f"/sys/block/{disk}/queue/scheduler"
            if os.path.exists(scheduler_path):
                with open(scheduler_path, "r") as f:
                    current_scheduler = f.read().strip()
                    
                # Guardar el scheduler original
                if "[" in current_scheduler:
                    # Extraer el scheduler activo
                    current_scheduler = re.search(r'\[(.*?)\]', current_scheduler).group(1)
                
                changes["original_values"][f"{disk}_scheduler"] = current_scheduler
                
                # Establecer el scheduler adecuado
                scheduler = ""
                if disk in ssds:
                    # Mejores schedulers para SSD
                    if "none" in open(scheduler_path).read():
                        scheduler = "none"
                    elif "mq-deadline" in open(scheduler_path).read():
                        scheduler = "mq-deadline"
                    elif "deadline" in open(scheduler_path).read():
                        scheduler = "deadline"
                else:
                    # Mejores schedulers para HDD
                    if "bfq" in open(scheduler_path).read():
                        scheduler = "bfq"
                    elif "cfq" in open(scheduler_path).read():
                        scheduler = "cfq"
                    elif "deadline" in open(scheduler_path).read():
                        scheduler = "deadline"
                
                if scheduler:
                    with open(scheduler_path, "w") as f:
                        f.write(scheduler)
                    changes["actions"].append(f"set {disk} scheduler to {scheduler}")
                    
                # Optimizar otros parámetros de la cola
                if disk in ssds:
                    # Optimizar para SSD
                    read_ahead_kb = "256"
                else:
                    # Optimizar para HDD
                    read_ahead_kb = "1024"
                
                read_ahead_path = f"/sys/block/{disk}/queue/read_ahead_kb"
                if os.path.exists(read_ahead_path):
                    with open(read_ahead_path, "r") as f:
                        changes["original_values"][f"{disk}_read_ahead_kb"] = f.read().strip()
                    
                    with open(read_ahead_path, "w") as f:
                        f.write(read_ahead_kb)
                    changes["actions"].append(f"set {disk} read_ahead_kb to {read_ahead_kb}")
    
    save_changes(changes)
    print(f"{Colors.GREEN}✓ Optimización de parámetros del kernel completada{Colors.ENDC}")
    return changes

def optimize_storage():
    """Optimiza la configuración de almacenamiento para SSD/HDD"""
    print(f"\n{Colors.BOLD}💽 Optimizando almacenamiento (SSD/HDD)...{Colors.ENDC}")
    changes = {"type": "storage", "actions": [], "original_values": {}}
    
    # Detectar discos
    success, output = run_command("lsblk -d -o NAME -n")
    disks = [disk.strip() for disk in output.split('\n') if disk.strip() and not disk.startswith("loop")]
    
    # Detectar SSDs
    ssds = []
    for disk in disks:
        success, output = run_command(f"cat /sys/block/{disk}/queue/rotational")
        if success and output.strip() == "0":
            ssds.append(disk)
    
    # Configurar TRIM para SSD
    if ssds:
        # Activar TRIM periódico vía fstrim.timer
        success, output = run_command("systemctl enable fstrim.timer")
        if success:
            changes["actions"].append("enabled periodic TRIM via fstrim.timer")
        
        # Configurar noatime en fstab para reducir escrituras
        fstab_path = "/etc/fstab"
        backup_path = save_backup(fstab_path)
        if backup_path:
            if "original_files" not in changes:
                changes["original_files"] = {}
            changes["original_files"][fstab_path] = backup_path
        
        with open(fstab_path, "r") as f:
            fstab_lines = f.readlines()
        
        new_fstab_lines = []
        for line in fstab_lines:
            # Solo procesar líneas que no sean comentarios y tengan un punto de montaje
            if not line.strip().startswith("#") and len(line.split()) >= 3:
                parts = line.split()
                mount_options = parts[3]
                
                # Si no tiene noatime o relatime, añadirlo
                if "noatime" not in mount_options and "relatime" not in mount_options and mount_options != "defaults":
                    parts[3] = mount_options + ",noatime"
                elif mount_options == "defaults":
                    parts[3] = "defaults,noatime"
                
                new_line = "\t".join(parts) + "\n"
                new_fstab_lines.append(new_line)
            else:
                new_fstab_lines.append(line)
        
        with open(fstab_path, "w") as f:
            f.writelines(new_fstab_lines)
        
        changes["actions"].append("added noatime to mount options in fstab")
    
    # Optimizar parámetros de HDD
    hdds = [disk for disk in disks if disk not in ssds]
    for hdd in hdds:
        # Configurar Advanced Power Management (APM)
        success, output = run_command(f"hdparm -B 254 /dev/{hdd}")
        if success:
            changes["actions"].append(f"set APM level for /dev/{hdd}")
        
        # Aumentar el tiempo de espera para la reducción de energía (spindown)
        success, output = run_command(f"hdparm -S 120 /dev/{hdd}")
        if success:
            changes["actions"].append(f"increased spindown timeout for /dev/{hdd}")
    
    # Activar DISCARD para SSD en /etc/lvm/lvm.conf si existe
    lvm_conf = "/etc/lvm/lvm.conf"
    if os.path.exists(lvm_conf) and ssds:
        backup_path = save_backup(lvm_conf)
        if backup_path:
            if "original_files" not in changes:
                changes["original_files"] = {}
            changes["original_files"][lvm_conf] = backup_path
        
        success, output = run_command("grep -n \"issue_discards\" /etc/lvm/lvm.conf")
        if success:
            line_num = output.split(":")[0]
            run_command(f"sed -i '{line_num}s/.*/\tissue_discards = 1/' {lvm_conf}")
            changes["actions"].append("enabled SSD TRIM support in LVM")
    
    # Activar compresión en systemas BTRFS
    success, output = run_command("mount | grep btrfs")
    if success and output.strip():
        print(f"{Colors.BLUE}Se han detectado particiones BTRFS. ¿Desea activar la compresión zstd para mejorar el rendimiento y ahorro de espacio?{Colors.ENDC}")
        choice = input(f"Activar compresión BTRFS [s/N]: ")
        
        if choice.lower() == "s":
            # Configurar compresión en fstab para todas las particiones BTRFS
            with open(fstab_path, "r") as f:
                fstab_lines = f.readlines()
            
            new_fstab_lines = []
            for line in fstab_lines:
                if not line.strip().startswith("#") and "btrfs" in line:
                    parts = line.split()
                    mount_options = parts[3]
                    
                    if "compress=" not in mount_options:
                        if mount_options == "defaults":
                            parts[3] = "defaults,compress=zstd:3"
                        else:
                            parts[3] = mount_options + ",compress=zstd:3"
                        
                        new_line = "\t".join(parts) + "\n"
                        new_fstab_lines.append(new_line)
                        changes["actions"].append(f"added zstd compression to BTRFS mount {parts[1]}")
                    else:
                        new_fstab_lines.append(line)
                else:
                    new_fstab_lines.append(line)
            
            with open(fstab_path, "w") as f:
                f.writelines(new_fstab_lines)
            
            # Aplicar compresión a las particiones BTRFS actualmente montadas
            success, output = run_command("mount | grep btrfs | awk '{print $3}'")
            if success:
                for mount_point in output.strip().split('\n'):
                    if mount_point:
                        success, output = run_command(f"btrfs filesystem defrag -r -v -czstd {mount_point}")
                        if success:
                            changes["actions"].append(f"applied zstd compression to {mount_point}")
    
    save_changes(changes)
    print(f"{Colors.GREEN}✓ Optimización de almacenamiento completada{Colors.ENDC}")
    return changes

def optimize_gaming():
    """Activa optimizaciones específicas para juegos"""
    print(f"\n{Colors.BOLD}🎮 Activando modo gaming...{Colors.ENDC}")
    changes = {"type": "gaming", "actions": [], "original_values": {}}
    
    # Guardar configuración original de CPU governor
    success, output = run_command("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
    if success:
        changes["original_values"]["cpu_governor"] = output.strip()
    
    # Cambiar al governor performance
    success, output = run_command("echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor", shell=True)
    if success:
        changes["actions"].append("set CPU governor to performance")
    
    # Desactivar el modo de ahorro de energía de la GPU (si es NVIDIA)
    success, output = run_command("which nvidia-settings")
    if success:
        success, output = run_command("nvidia-settings -a [gpu:0]/GpuPowerMizerMode=1")
        if success:
            changes["actions"].append("disabled NVIDIA power saving mode")
    
    # Reducir la latencia del kernel
    sysctl_conf = "/etc/sysctl.conf"
    backup_path = save_backup(sysctl_conf)
    if backup_path and "original_files" not in changes:
        changes["original_files"] = {sysctl_conf: backup_path}
    
    # Parámetros para mejorar la latencia
    gaming_params = [
        ("kernel.sched_min_granularity_ns", "10000000"),
        ("kernel.sched_wakeup_granularity_ns", "15000000"),
        ("vm.stat_interval", "10"),
        ("kernel.timer_migration", "0")
    ]
    
    # Leer el archivo actual
    with open(sysctl_conf, "r") as f:
        current_content = f.read()
    
    # Añadir optimizaciones de gaming
    with open(sysctl_conf, "a") as f:
        f.write("\n# Optimizaciones para gaming añadidas por AutoTweak\n")
        
        for param, value in gaming_params:
            # Verificar si el parámetro ya existe
            regex = re.compile(f"^{param.replace('.', '\\.')}\\s*=", re.MULTILINE)
            if regex.search(current_content):
                # Si existe, obtenemos el valor actual
                success, original_value = run_command(f"sysctl -n {param}")
                if success:
                    changes["original_values"][param] = original_value.strip()
                
                # Actualizamos con el nuevo valor
                success, output = run_command(f"sysctl -w {param}={value}")
                if success:
                    changes["actions"].append(f"updated {param}={value}")
                
                continue
            
            # Guardar valor original
            success, original_value = run_command(f"sysctl -n {param}")
            if success:
                changes["original_values"][param] = original_value.strip()
            
            # Aplicar nuevo valor
            success, output = run_command(f"sysctl -w {param}={value}")
            if success:
                changes["actions"].append(f"set {param}={value}")
                f.write(f"{param}={value}\n")
    
    # Configurar prioridad de procesos para juegos
    # Crear script para ejecutar juegos con mayor prioridad
    game_launcher_path = "/usr/local/bin/game-launcher"
    with open(game_launcher_path, "w") as f:
        f.write("""#!/bin/bash
# Script para lanzar juegos con mayor prioridad
if [ $# -eq 0 ]; then
    echo "Uso: game-launcher <comando del juego>"
    exit 1
fi

# Ejecutar el juego con nice -10 (prioridad más alta)
nice -n -10 "$@" &
PID=$!

# Configurar el proceso para usar menos E/S
ionice -c 2 -n 0 -p $PID

# Establecer política de programación en SCHED_RR (round-robin en tiempo real)
chrt -r -p 50 $PID

wait $PID
""")
    
    run_command(f"chmod +x {game_launcher_path}")
    changes["actions"].append("created game-launcher script")
    
    # Instalar herramientas de optimización de gaming según la distribución
    distro = detect_distro()
    
    if distro == "debian":
        # Para Ubuntu/Debian
        run_command("apt-get install -y gamemode")
        changes["actions"].append("installed gamemode")
    elif distro == "arch":
        # Para Arch
        run_command("pacman -S --noconfirm gamemode lib32-gamemode")
        changes["actions"].append("installed gamemode and lib32-gamemode")
    elif distro == "fedora":
        # Para Fedora
        run_command("dnf install -y gamemode")
        changes["actions"].append("installed gamemode")
    
    save_changes(changes)
    print(f"{Colors.GREEN}✓ Modo gaming activado{Colors.ENDC}")
    return changes

def restore_changes():
    """Revierte los cambios realizados por AutoTweak"""
    if not os.path.exists(CHANGES_FILE):
        print(f"{Colors.WARNING}No se encontraron cambios para revertir.{Colors.ENDC}")
        return False
    
    print(f"\n{Colors.BOLD}↩️ Revirtiendo cambios...{Colors.ENDC}")
    
    with open(CHANGES_FILE, 'r') as f:
        try:
            all_changes = json.load(f)
        except json.JSONDecodeError:
            print(f"{Colors.FAIL}Error al leer el archivo de cambios.{Colors.ENDC}")
            return False
    
    if not all_changes:
        print(f"{Colors.WARNING}No hay cambios para revertir.{Colors.ENDC}")
        return False
    
    # Mostrar cambios disponibles para revertir
    print(f"\n{Colors.BLUE}Cambios disponibles para revertir:{Colors.ENDC}")
    for i, change in enumerate(all_changes):
        timestamp = change.get('timestamp', 'Desconocido')
        change_type = change.get('type', 'Desconocido')
        print(f"{i+1}. [{timestamp}] Tipo: {change_type} - {len(change.get('actions', []))} acciones")
    
    choice = input(f"\n{Colors.BOLD}Seleccione el cambio a revertir (1-{len(all_changes)}) o 'todos' para revertir todo: {Colors.ENDC}")
    
    changes_to_revert = []
    if choice.lower() == 'todos':
        changes_to_revert = all_changes
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(all_changes):
                changes_to_revert = [all_changes[idx]]
            else:
                print(f"{Colors.FAIL}Selección inválida.{Colors.ENDC}")
                return False
        except ValueError:
            print(f"{Colors.FAIL}Entrada inválida.{Colors.ENDC}")
            return False
    
    # Revertir los cambios seleccionados
    for change in changes_to_revert:
        change_type = change.get('type', 'unknown')
        print(f"\n{Colors.BOLD}Revirtiendo cambios de tipo: {change_type}{Colors.ENDC}")
        
        # Restaurar archivos de configuración originales
        if 'original_files' in change:
            for file_path, backup_path in change['original_files'].items():
                if os.path.exists(backup_path):
                    shutil.copy2(backup_path, file_path)
                    print(f"{Colors.GREEN}Restaurado {file_path} desde backup{Colors.ENDC}")
        
        # Restaurar valores originales de configuración
        if 'original_values' in change:
            for param, value in change['original_values'].items():
                if param.startswith("vm.") or param.startswith("kernel.") or param.startswith("net."):
                    run_command(f"sysctl -w {param}={value}")
                    print(f"{Colors.GREEN}Restaurado {param}={value}{Colors.ENDC}")
                elif param.endswith("_scheduler"):
                    disk = param.split("_")[0]
                    scheduler_path = f"/sys/block/{disk}/queue/scheduler"
                    if os.path.exists(scheduler_path):
                        with open(scheduler_path, "w") as f:
                            f.write(value)
                        print(f"{Colors.GREEN}Restaurado scheduler de {disk} a {value}{Colors.ENDC}")
                elif param.endswith("_read_ahead_kb"):
                    disk = param.split("_")[0]
                    read_ahead_path = f"/sys/block/{disk}/queue/read_ahead_kb"
                    if os.path.exists(read_ahead_path):
                        with open(read_ahead_path, "w") as f:
                            f.write(value)
                        print(f"{Colors.GREEN}Restaurado read_ahead_kb de {disk} a {value}{Colors.ENDC}")
                elif param == "cpu_governor":
                    run_command(f"echo {value} | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor", shell=True)
                    print(f"{Colors.GREEN}Restaurado CPU governor a {value}{Colors.ENDC}")
        
        # Habilitar servicios deshabilitados
        if 'disabled_services' in change:
            for service in change['disabled_services']:
                run_command(f"systemctl enable {service}")
                print(f"{Colors.GREEN}Re-habilitado servicio {service}{Colors.ENDC}")
    
    # Actualizar el archivo de cambios
    remaining_changes = [c for c in all_changes if c not in changes_to_revert]
    with open(CHANGES_FILE, 'w') as f:
        json.dump(remaining_changes, f, indent=4)
    
    print(f"\n{Colors.GREEN}✓ Cambios revertidos correctamente{Colors.ENDC}")
    return True

def show_system_info():
    """Muestra información del sistema"""
    print(f"\n{Colors.BOLD}📊 Información del sistema:{Colors.ENDC}\n")
    
    # Información del SO
    success, distro_info = run_command("cat /etc/os-release")
    if success:
        for line in distro_info.split('\n'):
            if line.startswith('PRETTY_NAME='):
                distro_name = line.split('=')[1].strip('"')
                print(f"{Colors.BLUE}Distribución:{Colors.ENDC} {distro_name}")
    
    # Kernel
    success, kernel = run_command("uname -r")
    if success:
        print(f"{Colors.BLUE}Kernel:{Colors.ENDC} {kernel.strip()}")
    
    # CPU
    success, cpu_info = run_command("lscpu | grep 'Model name'")
    if success and cpu_info:
        cpu_model = cpu_info.split(':')[1].strip()
        print(f"{Colors.BLUE}CPU:{Colors.ENDC} {cpu_model}")
    
    # Memoria
    success, mem_info = run_command("free -h")
    if success:
        mem_lines = mem_info.strip().split('\n')
        if len(mem_lines) > 1:
            mem_parts = mem_lines[1].split()
            if len(mem_parts) >= 2:
                print(f"{Colors.BLUE}Memoria:{Colors.ENDC} {mem_parts[1]}")
    
    # Discos
    print(f"\n{Colors.BLUE}Almacenamiento:{Colors.ENDC}")
    run_command("df -h | grep -v tmpfs")
    
    # Detectar SSD vs HDD
    print(f"\n{Colors.BLUE}Tipos de discos:{Colors.ENDC}")
    success, disks = run_command("lsblk -d -o NAME -n")
    if success:
        for disk in disks.strip().split('\n'):
            if disk and not disk.startswith("loop"):
                success, rotational = run_command(f"cat /sys/block/{disk}/queue/rotational")
                if success:
                    disk_type = "HDD" if rotational.strip() == "1" else "SSD"
                    print(f"  {disk}: {disk_type}")
    
    # Servicios activos
    print(f"\n{Colors.BLUE}Servicios activos:{Colors.ENDC} ", end="")
    success, active_services = run_command("systemctl list-units --type=service --state=active | wc -l")
    if success:
        print(active_services.strip())
    
    # Tiempo de arranque
    print(f"{Colors.BLUE}Tiempo de arranque:{Colors.ENDC} ", end="")
    success, boot_time = run_command("systemd-analyze")
    if success:
        print(boot_time.strip())
    
    return

def main_menu():
    """Muestra el menú principal interactivo"""
    while True:
        print_banner()
        print(f"\n{Colors.BOLD}📋 Menú Principal:{Colors.ENDC}")
        print(f"1. {Colors.GREEN}Ejecutar todas las optimizaciones{Colors.ENDC}")
        print(f"2. {Colors.BLUE}🧹 Limpieza del sistema{Colors.ENDC}")
        print(f"3. {Colors.BLUE}💾 Optimización de RAM y SWAP{Colors.ENDC}")
        print(f"4. {Colors.BLUE}🚀 Optimización de arranque{Colors.ENDC}")
        print(f"5. {Colors.BLUE}⚙️ Optimización de parámetros del kernel{Colors.ENDC}")
        print(f"6. {Colors.BLUE}💽 Optimización de almacenamiento (SSD/HDD){Colors.ENDC}")
        print(f"7. {Colors.BLUE}🎮 Activar modo gaming{Colors.ENDC}")
        print(f"8. {Colors.WARNING}↩️ Revertir cambios{Colors.ENDC}")
        print(f"9. {Colors.BLUE}📊 Mostrar información del sistema{Colors.ENDC}")
        print(f"0. {Colors.FAIL}Salir{Colors.ENDC}")
        
        choice = input(f"\n{Colors.BOLD}Seleccione una opción (0-9): {Colors.ENDC}")
        
        if choice == "1":
            distro = detect_distro()
            if distro == "unknown":
                print(f"{Colors.WARNING}No se pudo detectar la distribución Linux. Se intentará continuar de todas formas.{Colors.ENDC}")
            else:
                print(f"{Colors.GREEN}Distribución detectada: {distro}{Colors.ENDC}")
            
            clean_system(distro)
            optimize_ram_swap()
            optimize_boot()
            optimize_kernel()
            optimize_storage()
            
            print(f"\n{Colors.BLUE}¿Desea activar también el modo gaming? [s/N]: {Colors.ENDC}")
            gaming_choice = input()
            if gaming_choice.lower() == "s":
                optimize_gaming()
            
            print(f"\n{Colors.GREEN}¡Todas las optimizaciones completadas con éxito!{Colors.ENDC}")
            print(f"{Colors.BOLD}Se recomienda reiniciar el sistema para aplicar todos los cambios.{Colors.ENDC}")
            input("\nPresione Enter para continuar...")
        
        elif choice == "2":
            distro = detect_distro()
            clean_system(distro)
            input("\nPresione Enter para continuar...")
        
        elif choice == "3":
            optimize_ram_swap()
            input("\nPresione Enter para continuar...")
        
        elif choice == "4":
            optimize_boot()
            input("\nPresione Enter para continuar...")
        
        elif choice == "5":
            optimize_kernel()
            input("\nPresione Enter para continuar...")
        
        elif choice == "6":
            optimize_storage()
            input("\nPresione Enter para continuar...")
        
        elif choice == "7":
            optimize_gaming()
            input("\nPresione Enter para continuar...")
        
        elif choice == "8":
            restore_changes()
            input("\nPresione Enter para continuar...")
        
        elif choice == "9":
            show_system_info()
            input("\nPresione Enter para continuar...")
        
        elif choice == "0":
            print(f"\n{Colors.GREEN}¡Gracias por usar AutoTweak!{Colors.ENDC}")
            break
        
        else:
            print(f"{Colors.FAIL}Opción inválida. Por favor, intente de nuevo.{Colors.ENDC}")
            time.sleep(1)

if __name__ == "__main__":
    try:
        # Verificar permisos de root
        check_root()
        
        # Iniciar menú interactivo
        main_menu()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Operación cancelada por el usuario.{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        print(f"\n{Colors.FAIL}Error inesperado: {str(e)}{Colors.ENDC}")
        print(f"\nConsulte el log para más detalles: {log_file}")
        sys.exit(1)
