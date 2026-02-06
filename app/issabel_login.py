import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# ==========================
# VARIABLES DE ENTORNO
# ==========================
EMAIL = os.getenv("ISSABEL_EMAIL")
PASSWORD = os.getenv("ISSABEL_PASSWORD")

if not EMAIL or not PASSWORD:
    raise RuntimeError("Faltan variables ISSABEL_EMAIL o ISSABEL_PASSWORD")

# Carpeta donde se guardara el CSV
DOWNLOAD_DIR = "/data/incoming/"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ==========================
# CHROME OPTIONS
# ==========================
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

prefs = {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
}
options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 20)

try:
    driver.get("https://mt.issabel.com/#!/login")

    # EMAIL
    email = wait.until(EC.element_to_be_clickable((By.ID, "email")))
    email.send_keys(EMAIL)

    # PASSWORD
    password = wait.until(EC.element_to_be_clickable((By.ID, "password")))
    password.send_keys(PASSWORD)

    # BOTON LOGIN
    boton = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
    boton.click()

    # MENU
    menu = wait.until(EC.element_to_be_clickable((By.XPATH, "//md-icon[contains(@class,'zmdi-menu')]")))
    menu.click()
    time.sleep(1)

    # CDR
    cdr_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'CDR')]")))
    cdr_btn.click()
    time.sleep(1)

    # LISTADO
    listado_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Listado')]")))
    listado_btn.click()
    time.sleep(2)

    # BOTON DESCARGA CSV
    download_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Exportar llamadas filtradas a CSV']"))
    )

    driver.execute_script("arguments[0].scrollIntoView(true);", download_btn)
    time.sleep(1)
    download_btn.click()

    # Esperar descarga
    time.sleep(15)

    print("CSV descargado correctamente en /data")

finally:
    driver.quit()


