import pygame
import sys
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import random
import time
import pygame.gfxdraw # Importa gfxdraw (opcional)

matplotlib.use("Agg")

# --------- Inicialização ----------
pygame.init()
pygame.font.init()

WIDTH, HEIGHT = 1200, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simulador de Fermentação de Pão - Versão Educacional")

# --------- Cores / Fontes ----------
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (230, 230, 230)
DARK_GRAY = (100, 100, 100)
BLUE = (70, 130, 180)
GREEN = (34, 139, 34)
RED = (178, 34, 34)
YELLOW = (255, 200, 0)
ORANGE = (255, 140, 0)
BEIGE = (245, 222, 179)
LIGHT_BROWN = (210, 180, 140)

# Paleta de cores temática
COLORS = {
    "background": (245, 245, 245),
    "panel": (255, 255, 255),
    "primary": (70, 130, 180),
    "secondary": (34, 139, 34),
    "accent": (178, 34, 34),
    "text": (50, 50, 50),
    "success": (65, 140, 75),
    "warning": (200, 150, 30),
    "error": (190, 45, 45),
    "highlight": (255, 215, 0),
    "ingredient_unselected": (220, 220, 220),
    "ingredient_selected": (180, 210, 230),
    "beige": (245, 222, 179)
}

FONT = pygame.font.SysFont("Arial", 18)
TITLE_FONT = pygame.font.SysFont("Arial", 26, bold=True)
LARGE_FONT = pygame.font.SysFont("Arial", 32, bold=True)

# --------- Constantes Científicas ----------
YEAST_GROWTH_RATE = 0.4  # h⁻¹ (Taxa de crescimento base da levedura)

# --------- Estado global ----------
state = "config"
simulation_speed = 1.0
simulation_finished = False
mensagem_debug = ""

# Fatos educacionais flutuantes
current_fact = None
fact_display_time = 0
FACT_DURATION = 150 # 5 segundos a 30 FPS

# --------- Slider class (clique + arrasta) ----------
active_slider = None  # slider sendo arrastado

class Slider:
    def __init__(self, x, y, w, h, min_val, max_val, start_val, label):
        self.rect = pygame.Rect(x, y, w, h)
        self.min_val = float(min_val)
        self.max_val = float(max_val)
        self.value = float(start_val)
        self.label = label
        self.handle_w = 12
        self.handle_rect = pygame.Rect(x, y, self.handle_w, h)
        self.dragging = False
        self.hovered = False
        self.update_handle()

    def update_handle(self):
        ratio = (self.value - self.min_val) / (self.max_val - self.min_val) if (self.max_val - self.min_val) != 0 else 0
        ratio = max(0.0, min(1.0, ratio))
        self.handle_rect.x = self.rect.x + int(ratio * (self.rect.w - self.handle_w))
        self.handle_rect.y = self.rect.y

    def draw(self, surface):
        pygame.draw.rect(surface, GRAY, self.rect, border_radius=6)
        pygame.draw.rect(surface, BLUE, self.handle_rect, border_radius=6)
        # Visual feedback for hover/drag
        if self.dragging:
            pygame.draw.rect(surface, self._adjust_color(BLUE, 1.4), self.handle_rect, border_radius=6)
            pygame.draw.circle(surface, self._adjust_color(BLUE, 1.4), self.handle_rect.center, self.handle_w, 2)
        elif self.hovered:
            pygame.draw.rect(surface, self._adjust_color(BLUE, 1.2), self.handle_rect, border_radius=6)

        label_s = f"{self.label}: {self.value:.2f}"
        txt = FONT.render(label_s, True, BLACK)
        surface.blit(txt, (self.rect.x, self.rect.y - 22))

    def _adjust_color(self, color, factor):
        return tuple(min(255, int(c * factor)) for c in color)

    def update(self, pos):
        self.hovered = self.handle_rect.collidepoint(pos)

    def start_drag(self, pos):
        if self.handle_rect.collidepoint(pos) or self.rect.collidepoint(pos):
            self.dragging = True
            self.move(pos)
            self.hovered = True
            return True
        return False

    def stop_drag(self):
        self.dragging = False

    def move(self, pos):
        rel_x = pos[0] - self.rect.x - self.handle_w / 2
        ratio = rel_x / float(self.rect.w) if self.rect.w != 0 else 0.0
        ratio = max(0.0, min(1.0, ratio))
        self.value = self.min_val + ratio * (self.max_val - self.min_val)
        self.update_handle()

# --------- Sliders ----------
sliders = [
    Slider(50, 200, 240, 20, 50, 1000, 1000, "Farinha (g)"),
    Slider(50, 260, 240, 20, 0.3, 0.9, 0.68, "Água (fração)"),
    Slider(50, 320, 240, 20, 15, 40, 30, "Temperatura (°C)"),
    Slider(50, 380, 240, 20, 0, 100, 20, "Açúcar (g)"),
    Slider(50, 440, 240, 20, 0, 30, 15, "Sal (g)"),
    Slider(50, 500, 240, 20, 30, 1440, 240, "Tempo (min)") # ATUALIZADO
]


# --------- Botões ----------
class ImprovedButton:
    def __init__(self, x, y, w, h, text, color=COLORS["primary"], hover_color=None, text_color=WHITE, icon=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.hover_color = hover_color if hover_color else self._adjust_color(color, 1.2)
        self.text_color = text_color
        self.hovered = False
        self.pressed = False
        self.icon = icon
        self.animation_progress = 0
        self.original_y = y

    def _adjust_color(self, color, factor):
        return tuple(min(255, int(c * factor)) for c in color)

    def draw(self, surface):
        # Animação de hover
        if self.hovered and self.animation_progress < 1.0:
            self.animation_progress = min(1.0, self.animation_progress + 0.15)
        elif not self.hovered and self.animation_progress > 0.0:
            self.animation_progress = max(0.0, self.animation_progress - 0.15)

        # Cor interpolada
        base_color = self.color
        target_color = self.hover_color
        current_color = tuple(
            int(base_color[i] + (target_color[i] - base_color[i]) * self.animation_progress)
            for i in range(3)
        )

        # Efeito de clique
        top_color = self._adjust_color(current_color, 0.8) if self.pressed else current_color
        self.rect.y = self.original_y + 2 if self.pressed else self.original_y

        # Desenhar botão
        pygame.draw.rect(surface, top_color, self.rect, border_radius=8)
        pygame.draw.rect(surface, self._adjust_color(top_color, 0.7), self.rect, 2, border_radius=8)

        txt = FONT.render(self.text, True, self.text_color)
        text_x = self.rect.centerx - txt.get_width()//2
        text_y = self.rect.centery - txt.get_height()//2

        if self.icon:
            text_x += 15

        surface.blit(txt, (text_x, text_y))

    def update(self, pos, events):
        self.hovered = self.rect.collidepoint(pos)
        clicked = False

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.hovered:
                    self.pressed = True
            elif event.type == pygame.MOUSEBUTTONUP:
                if self.hovered and self.pressed:
                    clicked = True
                # Reset pressed state on any mouse up event
                self.pressed = False
        return clicked

# --------- Sistema de Tutoriais ----------
class TutorialSystem:
    def __init__(self):
        self.current_tip = None
        self.tip_time = 0
        self.tip_duration = 300  # frames
        self.completed_steps = set()
        
    def show_tip(self, tip_key, message):
        if tip_key not in self.completed_steps:
            self.current_tip = message
            self.tip_time = 0
            self.completed_steps.add(tip_key)
            
    def update(self):
        if self.current_tip:
            self.tip_time += 1
            if self.tip_time > self.tip_duration:
                self.current_tip = None
                
    def draw(self, surface):
        if self.current_tip:
            # Fundo semi-transparente
            s = pygame.Surface((WIDTH, 60), pygame.SRCALPHA)
            s.fill((0, 0, 0, 180))
            surface.blit(s, (0, HEIGHT - 60))
            
            # Texto da dica
            tip_text = FONT.render(self.current_tip, True, WHITE)
            surface.blit(tip_text, (WIDTH//2 - tip_text.get_width()//2, HEIGHT - 40))

# --------- Gerenciador de Telas ----------
class ScreenManager:
    def __init__(self):
        self.history = []
        
    def go_to(self, new_state):
        self.history.append(state)
        return new_state
        
    def go_back(self):
        if self.history:
            return self.history.pop()
        return "config" 

# --------- Botões ----------
start_button = ImprovedButton(50, 560, 100, 36, "Start", GREEN)
pause_button = ImprovedButton(170, 560, 100, 36, "Pause", RED)
reset_button = ImprovedButton(290, 560, 100, 36, "Reset", BLUE)
voltar_button = ImprovedButton(320, 610, 140, 30, "Voltar", RED) # Usado na simulação

# Botões de velocidade
speed_1x_button = ImprovedButton(50, 610, 80, 30, "1x", COLORS["primary"])
speed_2x_button = ImprovedButton(140, 610, 80, 30, "2x", COLORS["primary"])
speed_5x_button = ImprovedButton(230, 610, 80, 30, "5x", COLORS["primary"])

ver_relatorio_button = ImprovedButton(120, 600, 160, 40, "Ver Relatório", COLORS["success"])

# --------- Simulação / dados ----------
running_simulation = False
paused = False
sim_time = 0.0  

time_data = []
data_biom = []
data_sucrose = [] 
data_maltose = []
data_gluten_retention = [] 
data_co2 = []
data_volume = []
data_ph = []
data_etoh = []
data_prot = [] 

# Variável para controlar debug
show_debug = False

# Função de debug
def debug_text(text, x=10, y=10, color=(255, 0, 0)):
    debug_font = pygame.font.SysFont("Arial", 16)
    text_surface = debug_font.render(str(text), True, color)
    screen.blit(text_surface, (x, y))

# --------- Bolhas de fermentação ----------
bubbles = []
def add_bubble():
    x = random.randint(95, 385) 
    y = 370 # Posição inicial no fundo
    size = random.randint(2, 6) # Bolhas menores
    speed = random.uniform(1.0, 2.5)
    bubbles.append({"x": x, "y": y, "size": size, "speed": speed})

def update_bubbles():
    for b in bubbles[:]:
        b["y"] -= b["speed"]
        b["size"] += 0.1 
        # Some se sair da tela ou atingir o tamanho máximo (8)
        if b["y"] < 220 or b["size"] > 8: 
            bubbles.remove(b)

# --------- Funções de fermentação ----------
def reset_simulation():
    global time_data, data_biom, data_sucrose, data_maltose, data_gluten_retention, data_co2, data_volume, data_ph, data_etoh, data_prot, running_simulation, paused, sim_time, simulation_finished
    time_data = []
    data_biom = []
    data_sucrose = []
    data_maltose = []
    data_gluten_retention = [] 
    data_co2 = []
    data_volume = []
    data_ph = []
    data_etoh = []
    data_prot = []
    running_simulation = False
    paused = False
    sim_time = 0.0
    simulation_finished = False 

def draw_finish_notice(surface):
    """Desenha um aviso de 'Simulação Concluída' sobre a tela."""
    # Desenha um fundo semi-transparente para focar o aviso
    s = pygame.Surface((400, 100), pygame.SRCALPHA)
    s.fill((0, 0, 0, 180)) # Preto, 180/255 de opacidade
    
    # Borda branca
    pygame.draw.rect(s, (255, 255, 255, 200), s.get_rect(), 2, border_radius=10)
    
    # Textos
    title_text = TITLE_FONT.render("Simulação Concluída", True, WHITE)
    info_text = FONT.render("Clique em 'Ver Relatório' para os resultados.", True, WHITE)
    
    # Posição centralizada
    s_x = ((WIDTH - 400) // 2) - 355
    s_y = ((HEIGHT - 100) // 2) - 250
    
    surface.blit(s, (s_x, s_y))
    surface.blit(title_text, (s_x + (400 - title_text.get_width()) // 2, s_y + 20))
    surface.blit(info_text, (s_x + (400 - info_text.get_width()) // 2, s_y + 55))


def update_simulation(t, temp, sugar_added, water, farina_g, salt_g):
    """
    Modelo de simulação "state-at-time-t" com consumo sequencial E cálculo de glúten.
    """

    # --- 1. Definição de Parâmetros Biológicos ---
    Y_X_S = 0.1; Y_E_S = 0.45; Y_C_S = 0.45
    MALT_FROM_STARCH = 0.05
    K_PROD_MALTOSE = 0.3; K_CONS_SUCROSE = 0.8; K_CONS_MALTOSE = 0.5
    N0 = 0.5; t_horas = t / 60.0

    # --- 2. Cálculo dos Fatores Ambientais ---
    optimal_temp = 30.0; width_low = 15.0; width_high = 7.0
    if temp < optimal_temp:
        temp_factor = np.exp(-0.5 * ((temp - optimal_temp) / width_low)**2)
    else:
        temp_factor = np.exp(-0.5 * ((temp - optimal_temp) / width_high)**2)
    temp_factor = max(0.01, temp_factor)

    water_factor = max(0.01, 1.0 - abs(water - 0.68) * 0.8)

    salt_percentage = salt_g / (farina_g + 1)
    salt_k_inhib = 23.0
    salt_factor = max(0.01, np.exp(-salt_k_inhib * salt_percentage))
    
    env_factor = temp_factor * water_factor * salt_factor

    # --- 3. Cálculo dos Açúcares (Modelo Sequencial) ---
    k_cons_suc = K_CONS_SUCROSE * env_factor
    sucrose_remaining = sugar_added * np.exp(-k_cons_suc * t_horas)

    k1 = K_PROD_MALTOSE * env_factor
    inhibition_factor = max(0.01, (sucrose_remaining / (sugar_added + 1e-6))**2)
    k2 = K_CONS_MALTOSE * env_factor * (1.0 - inhibition_factor)
    
    starch_potential = farina_g * MALT_FROM_STARCH
    k_diff = k2 - k1 + 1e-6
    
    maltose_at_t = starch_potential * (k1 / k_diff) * (np.exp(-k1 * t_horas) - np.exp(-k2 * t_horas))
    maltose_at_t = max(0, maltose_at_t)

    # --- 4. Cálculo dos Outros Produtos (Biomassa, CO2, etc.) ---
    total_sugar_potential = sugar_added + (farina_g * MALT_FROM_STARCH)
    K = max(N0 + 0.1, total_sugar_potential * Y_X_S)
    
    K_s_sugar = 10.0
    sugar_factor = total_sugar_potential / (K_s_sugar + total_sugar_potential)
    r = YEAST_GROWTH_RATE * sugar_factor * env_factor
    
    biom = K / (1 + ((K - N0)/N0) * np.exp(-r * t_horas))
    
    biomass_produced = biom - N0
    total_sugar_consumed = min(total_sugar_potential, biomass_produced / Y_X_S)
    
    sugar_for_fermentation = total_sugar_consumed * (Y_C_S + Y_E_S)
    co2 = sugar_for_fermentation * (Y_C_S / (Y_C_S + Y_E_S))
    etanol = sugar_for_fermentation * (Y_E_S / (Y_C_S + Y_E_S))

    base_volume = farina_g * 0.8
    
    volume = base_volume + co2 * 300 * (1 - np.exp(-t/180.0))
    
    acid_production = 0.015 * biom * (1 - np.exp(-t/120.0))
    ph = max(3.8, 5.6 - acid_production)

    # --- 5. CÁLCULO DA RETENÇÃO DE GLÚTEN ---
    retention = 100.0 # Começa em 100%

    # Efeito do Sal: Ótimo em 2%
    retention += (np.exp(-0.5 * ((salt_percentage - 0.02) / 0.01)**2) - 0.5) * 20 # Bônus/pênalti de +/- 10%
    
    # Efeito da Água: Ótimo em 70%
    retention -= abs(water - 0.70) * 30 # Pênalti por se afastar de 70%
    
    # Efeito do Ácido (pH): Degrada abaixo de 4.5
    retention -= max(0, (4.5 - ph)) * 40 # Pênalti forte por acidez
    
    # Efeito do Etanol: Degrada o glúten
    retention -= (etanol / (farina_g + 1)) * 300 # Pênalti por etanol
    
    # Limita o valor entre 5% e 98%
    retention = max(5.0, min(98.0, retention))

    # Retorna 8 valores
    return biom, sucrose_remaining, maltose_at_t, co2, volume, ph, etanol, retention

def draw_prediction_panel(surface, x, y, width, height, prediction):
    """
    Desenha o painel de feedback em tempo real na tela de configuração.
    """
    # Caixa de fundo
    panel_rect = pygame.Rect(x, y, width, height)
    pygame.draw.rect(surface, COLORS["panel"], panel_rect, border_radius=10)
    pygame.draw.rect(surface, COLORS["text"], panel_rect, 1, border_radius=10)
    
    # Título
    title_text = FONT.render("Painel de Previsão (Tempo Real)", True, COLORS["text"])
    surface.blit(title_text, (x + 20, y + 15))
    
    # Linha divisória
    pygame.draw.line(surface, GRAY, (x + 15, y + 45), (x + width - 15, y + 45), 1)
    
    # Métricas
    ph_text = FONT.render(f"pH Final Estimado: {prediction['ph']:.2f}", True, COLORS["text"])
    vol_text = FONT.render(f"Volume Final Estimado: {prediction['volume']:.0f} mL", True, COLORS["text"])
    ret_text = FONT.render(f"Retenção Glúten (Final): {prediction['retention']:.1f}%", True, COLORS["text"])
    
    surface.blit(ph_text, (x + 20, y + 60))
    surface.blit(vol_text, (x + 20, y + 85))
    surface.blit(ret_text, (x + 20, y + 110))
    
    # Feedback Qualitativo
    feedback_title = FONT.render("Análise:", True, prediction['color'])
    feedback_s = FONT.render(prediction['feedback'], True, prediction['color'])
    
    surface.blit(feedback_title, (x + 20, y + 145))
    surface.blit(feedback_s, (x + 20, y + 170))

def draw_educational_visual(progress):
    """Desenha visualização com elementos educacionais"""

    # --- Dimensões e Posições da "Bacia" ---
    basin_rect = pygame.Rect(75, 200, 340, 220) # Retângulo para a bacia
    basin_color = DARK_GRAY
    
    # Base da bacia (oval)
    pygame.draw.ellipse(screen, basin_color, basin_rect, 6)
    
    # --- CÁLCULO DE CRESCIMENTO ---
    farinha_g = sliders[0].value
    
    # 1. Volume Inicial (Base)
    # Este é o volume inicial real da massa (80% do peso da farinha).
    initial_base_volume = farinha_g * 0.8 
    
    # 2. Volume Atual
    # Pega o último valor de volume calculado pela simulação.
    current_volume = data_volume[-1] if data_volume else initial_base_volume
    
    # 3. Volume Máximo (Visual)
    # teto visual fixo. 120% de crescimento (2.2 * base)
    # como o ponto 100% visual, o mesmo usado na previsão.
    visual_max_volume = initial_base_volume * 2.2

    # 4. Proporção do Crescimento
    # (Quanto cresceu) / (Quanto esperamos que cresça no total)
    growth_so_far = current_volume - initial_base_volume
    total_expected_growth = visual_max_volume - initial_base_volume
    
    volume_growth_ratio = growth_so_far / max(0.1, total_expected_growth)
    volume_growth_ratio = max(0.0, min(1.0, volume_growth_ratio)) # Limita entre 0% e 100%
    
    # --- Cálculo da Altura da Massa ---
    min_dough_height = 60 # Altura mínima visível da massa
    max_dough_height = 160 # Altura máxima da massa
    
    dough_height = min_dough_height + int((max_dough_height - min_dough_height) * volume_growth_ratio)
    
    dough_width = basin_rect.width - 40 # Largura da massa dentro da bacia
    dough_x = basin_rect.x + (basin_rect.width - dough_width) // 2
    dough_y = basin_rect.y + (basin_rect.height - dough_height)
    
    dough_color_base = BEIGE 

    # --- Desenho da Massa (APENAS ELIPSE SIMPLES) ---
    dough_bottom_rect = pygame.Rect(dough_x, dough_y, dough_width, dough_height)
    pygame.draw.ellipse(screen, dough_color_base, dough_bottom_rect)
    
    # Sombreamento interno na bacia, abaixo da massa
    shadow_rect = pygame.Rect(basin_rect.x + 3, dough_y + dough_height - 10, basin_rect.width - 6, 15)
    shadow_surf = pygame.Surface(shadow_rect.size, pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0,0,0,50), shadow_surf.get_rect())
    screen.blit(shadow_surf, shadow_rect.topleft)

    # --- Bolhas de CO₂ Flutuando DENTRO da Massa ---
    for b in bubbles:
        if dough_x < b["x"] < dough_x + dough_width and dough_y < b["y"] < dough_y + dough_height:
            try:
                pygame.gfxdraw.aacircle(screen, int(b["x"]), int(b["y"]), int(b["size"]), (255, 255, 255, 150))
                pygame.gfxdraw.filled_circle(screen, int(b["x"]), int(b["y"]), int(b["size"]), (255, 255, 255, 150))
            except (AttributeError, ImportError):
                pygame.draw.circle(screen, (255, 255, 255, 150), (int(b["x"]), int(b["y"])), int(b["size"]))


    # --- Texto educacional flutuante ---
    global current_fact, fact_display_time
    if current_fact is None and random.random() < 0.005 and len(data_co2) > 10: 
        facts = [
            "As leveduras consomem açúcar e produzem CO₂!",
            "O CO₂ faz a massa crescer formando bolhas.",
            "O sal controla a levedura e fortalece o glúten.",
            "Acidez excessiva (pH baixo) degrada o glúten!",
            "A temperatura ideal para a levedura é ~30°C.",
            "Muita água pode deixar o glúten fraco."
        ]
        current_fact = random.choice(facts)
        fact_display_time = 0

    if current_fact:
        fact_display_time += 1
        fact_text = FONT.render(current_fact, True, COLORS["text"])
        
        fact_x = basin_rect.centerx - fact_text.get_width() // 2
        fact_y = basin_rect.top - fact_text.get_height() - 10
        screen.blit(fact_text, (fact_x, fact_y))
        
        if fact_display_time > FACT_DURATION:
            current_fact = None
            
    # --- Informações em tempo real com destaque visual ---
    y0 = 490
    if len(time_data) > 0:
        pygame.draw.rect(screen, GRAY, (75, y0, 340, 20), border_radius=4)
        pygame.draw.rect(screen, BLUE, (75, y0+5, int(340 * progress), 12), border_radius=8)
        
        phase_markers = [
            ("Adaptação", 0.0, RED),
            ("Crescimento", 0.3, ORANGE),
            ("Pico", 0.6, GREEN),
            ("Declínio", 1.0, BLUE)
        ]
        
        for phase, pos, color in phase_markers:
            marker_x = 75 + int(340 * pos)
            pygame.draw.line(screen, color, (marker_x, y0 - 5), (marker_x, y0 + 25), 2)
            phase_text = FONT.render(phase, True, color)
            screen.blit(phase_text, (marker_x - phase_text.get_width()//2, y0 - 25))
            
        indicators = [
            (f"Tempo: {time_data[-1]:.1f} min", 75, y0 + 30),
            (f"pH: {data_ph[-1]:.2f}", 200, y0 + 30),
            (f"CO₂: {data_co2[-1]:.2f} g", 325, y0 + 30),
            (f"Volume: {data_volume[-1]:.2f} mL", 75, y0 + 50),
            (f"Retenção Glúten: {data_gluten_retention[-1]:.1f}%", 200, y0 + 50)
        ]
            
        for text, x, y in indicators:
            txt = FONT.render(text, True, BLACK)
            screen.blit(txt, (x, y))


def get_prediction_feedback(params):
    """
    Calcula o estado final com base nos parâmetros atuais e retorna os dados e um feedback.
    """
    # Extrai os parâmetros dos sliders
    farina_g = params[0]
    water = params[1]
    temp = params[2]
    sugar_added = params[3]
    salt_g = params[4]
    time_limit = params[5] # Tempo final
    
    # Chama a simulação UMA VEZ para o tempo final
    biom, suc, malt, co2v, vol, phv, etoh, ret = update_simulation(time_limit, temp, sugar_added, water, farina_g, salt_g)
    
    # --- LÓGICA DE COMPARAÇÃO ---
    # O volume inicial da massa é aprox. 80% do peso da farinha
    base_volume = farina_g * 0.8 
    
    # --- Gera o Feedback Qualitativo ---
    feedback_text = ""
    color = COLORS["success"] # Verde por padrão
    
    # 1. Checagem de perigo (acidez/degradação)
    if phv < 4.1 or ret < 60:
        feedback_text = "Aviso: Risco de massa ácida e glúten degradado."
        color = COLORS["error"] # Vermelho
    
    # 2. Checagem de crescimento (baseado no volume relativo)
    elif vol > (base_volume * 2.2): # Cresceu mais que 120% (ex: 800mL -> > 1760mL)
        feedback_text = "Bom Volume final: Parâmetros parecem equilibrados."
        color = COLORS["success"]
    elif vol > (base_volume * 1.7): # Cresceu mais que 70% (ex: 800mL -> > 1360mL)
        feedback_text = "OK: Fermentação moderada."
        color = COLORS["primary"]
    else: # Cresceu menos de 70%
        feedback_text = "Crescimento Lento: Verifique sal, temperatura ou tempo."
        color = COLORS["warning"] # Laranja

    return {
        "ph": phv,
        "volume": vol,
        "retention": ret,
        "feedback": feedback_text,
        "color": color
    }



def create_improved_graphs():
    """Cria gráficos com melhor formatação e informações"""
    fig = plt.figure(figsize=(8, 6), dpi=100)
    
    ax1 = plt.subplot2grid((3, 2), (0, 0))
    ax2 = plt.subplot2grid((3, 2), (0, 1))
    ax3 = plt.subplot2grid((3, 2), (1, 0)) 
    ax4 = plt.subplot2grid((3, 2), (1, 1))
    ax5 = plt.subplot2grid((3, 2), (2, 0))
    ax6 = plt.subplot2grid((3, 2), (2, 1)) 
    
    plots = [
        (ax1, data_ph, "pH", "blue", "pH"),
        (ax2, data_biom, "Crescimento de Leveduras", "green", "g/L"),
        (ax3, data_sucrose, "Açúcares", "orange", "g"), 
        (ax4, data_co2, "Produção de CO₂", "red", "g"),
        (ax5, data_volume, "Volume da Massa", "purple", "mL"),
        (ax6, data_etoh, "Produção de Etanol", "brown", "g/L"),
    ]
    
    for ax, series, title, color, y_label in plots:
        ax.clear()
        label = title.split(" ")[0] # Label padrão
        if "Açúcares" in title:
            label = "Sacarose" # Label específica
            
        if len(time_data) > 0 and len(series) > 0:
            ax.plot(time_data, series, color=color, linewidth=2, label=label)
        ax.set_title(title, fontsize=10, pad=5)
        ax.set_xlabel("Tempo (min)", fontsize=8)
        ax.set_ylabel(y_label, fontsize=8)
        ax.grid(True, linestyle="--", alpha=0.7)
        
        # Ajustar limites do eixo Y com margem
        if "pH" in title:
            ax.set_ylim(3.5, 7.0)
        elif any(x in title for x in ["Leveduras", "Bacteriano", "Biomassa"]):
            if len(series) > 0: mx = max(series); ax.set_ylim(0, mx * 1.2 if mx > 0 else 10)
        elif "Volume" in title:
            if len(series) > 0: mx = max(series); ax.set_ylim(min(series)*0.9, max(2, mx * 1.2))
        elif "CO₂" in title or "Ácido" in title or "Etanol" in title: 
            if len(series) > 0: mx = max(series); ax.set_ylim(0, max(1, mx * 1.2))
        elif "Açúcares" in title:
             if len(data_sucrose) > 0 and len(data_maltose) > 0:
                mx = max(max(data_sucrose), max(data_maltose))
                ax.set_ylim(0, max(10, mx * 1.1))
             elif len(data_sucrose) > 0:
                 mx = max(data_sucrose)
                 ax.set_ylim(0, max(10, mx * 1.1))

    # Plotar Maltose no ax3
    if len(time_data) > 0 and len(data_maltose) > 0:
        ax3.plot(time_data, data_maltose, color='deepskyblue', linewidth=2, label="Maltose")
    
    # Adicionar legenda apenas ao gráfico de açúcares
    ax3.legend(fontsize='small')
    
    plt.tight_layout()
    canvas = FigureCanvas(fig)
    canvas.draw()
    raw = canvas.buffer_rgba()
    raw_bytes = raw.tobytes()
    size = canvas.get_width_height()
    plt.close(fig)
    return pygame.image.frombuffer(raw_bytes, size, "RGBA")

def generate_analysis():
    """Gera análise educacional baseada nos resultados"""
    analyses = []
    
    # Parâmetros usados na simulação
    farinha_g = sliders[0].value
    base_volume = farinha_g * 0.8 
    
    # Resultados da simulação
    max_volume = max(data_volume) if data_volume else base_volume
    final_ph = data_ph[-1] if data_ph else 7
    final_etoh = data_etoh[-1] if data_etoh else 0
    
    # --- LÓGICA DE ANÁLISE ---
    # Análise do Volume (Crescimento)
    if final_ph < 4.1: # Priorizar checagem de perigo
        analyses.append(f"✗ Crescimento parado. A massa ficou muito ácida (pH {final_ph:.2f}), inibindo a levedura.")
    elif max_volume > (base_volume * 2.2): # Cresceu mais que 120%
        analyses.append(f"✓ Excelente crescimento! A produção de CO₂ ({max(data_co2):.1f}g) foi vigorosa e a massa atingiu {max_volume:.0f} mL.")
    elif max_volume > (base_volume * 1.7): # Cresceu mais que 70%
        analyses.append(f"✓ Bom crescimento. A massa desenvolveu um volume adequado ({max_volume:.0f} mL).")
    else:
        analyses.append(f"✗ Crescimento limitado ({max_volume:.0f} mL). Verifique se o tempo foi curto ou se os parâmetros (sal, temp) inibiram a levedura.")
        
    # Análise do pH (Acidez e Sabor)
    if 4.0 <= final_ph <= 4.8:
        analyses.append(f"✓ O pH final ({final_ph:.2f}) está na faixa ideal, sugerindo um pão com sabor bem desenvolvido.")
    elif final_ph > 4.8:
        analyses.append(f"✗ O pH ({final_ph:.2f}) ficou um pouco alto. A fermentação pode não ter sido longa o suficiente para desenvolver acidez.")
    else: # Já coberto pela análise de volume, mas reforçado aqui
        analyses.append(f"✗ O pH ({final_ph:.2f}) está muito baixo, resultando em um pão excessivamente ácido (azedo).")

    # Análise do Etanol (Aroma)
    if final_etoh > (farinha_g * 0.003): # (ex: > 3g para 1000g de farinha)
        analyses.append(f"✓ A produção de etanol ({final_etoh:.1f}g) foi significativa, contribuindo para o aroma.")
    else:
        analyses.append(f"✓ Produção de etanol moderada ({final_etoh:.1f}g). Normal para fermentações mais curtas.")
        
    return analyses

def create_educational_report():
    """Cria relatório educativo final"""
    report_surface = pygame.Surface((WIDTH, HEIGHT))
    report_surface.fill(COLORS["background"])
    
    # --- Coluna Esquerda (Parâmetros e Análise) ---
    # Cabeçalho
    title = TITLE_FONT.render("Relatório da Simulação", True, COLORS["text"])
    report_surface.blit(title, (WIDTH//2 - title.get_width()//2, 20))
    
    coluna_esquerda = pygame.Rect(20, 70, 450, HEIGHT - 100)
    coluna_direita = pygame.Rect(500, 70, WIDTH - 520, HEIGHT - 100)
    
    pygame.draw.rect(report_surface, COLORS["panel"], coluna_esquerda, border_radius=10)
    pygame.draw.rect(report_surface, COLORS["panel"], coluna_direita, border_radius=10)
    pygame.draw.rect(report_surface, COLORS["text"], coluna_esquerda, 1, border_radius=10)
    pygame.draw.rect(report_surface, COLORS["text"], coluna_direita, 1, border_radius=10)
    
    y_pos = 90
    params = [
        f"Farinha: {sliders[0].value:.2f}g",
        f"Hidratação: {sliders[1].value * 100:.0f}%",
        f"Temperatura: {sliders[2].value:.1f}°C",
        f"Açúcar: {sliders[3].value:.1f}g",
        f"Sal: {sliders[4].value:.1f}g"
    ]
    
    titulo_params = FONT.render("Parâmetros Utilizados:", True, COLORS["text"])
    report_surface.blit(titulo_params, (40, y_pos))
    y_pos += 30
    
    for param in params:
        text = FONT.render(param, True, COLORS["text"])
        report_surface.blit(text, (50, y_pos))
        y_pos += 25
    
    # Análise dos resultados (A análise de Glúten é MANTIDA aqui)
    if len(time_data) > 0:
        y_pos += 20
        analysis_title = FONT.render("Análise dos Resultados:", True, COLORS["text"])
        report_surface.blit(analysis_title, (40, y_pos))
        y_pos += 30
        
        # Gerar análise
        analyses = generate_analysis()
        
        # Análise de Glúten (MANTIDA)
        final_gluten = data_gluten_retention[-1] if data_gluten_retention else 0
        if final_gluten > 80:
             analyses.append(f"✓ Retenção de glúten excelente ({final_gluten:.0f})%. Os parâmetros de sal, água e tempo foram ideais.")
        elif final_gluten > 60:
             analyses.append(f"✓ Boa retenção de glúten ({final_gluten:.0f})%. A rede está forte.")
        else:
             analyses.append(f"✗ Retenção de glúten baixa ({final_gluten:.0f})%. Verifique se o tempo foi muito longo (acidez) ou se os parâmetros de sal/água estão corretos.")

        max_width = coluna_esquerda.width - 40
        for analysis in analyses:
            lines = wrap_text(analysis, FONT, max_width)
            for line in lines:
                text = FONT.render(line, True, COLORS["text"])
                report_surface.blit(text, (60, y_pos))
                y_pos += 25

    # --- Coluna Direita (Gráfico Normalizado) ---
    
    if len(time_data) > 0:
        fig = plt.figure(figsize=(6, 4.5), dpi=100)
        ax = fig.add_subplot(111)

        def to_mpl_color(c):
            return (c[0]/255.0, c[1]/255.0, c[2]/255.0)

        def normalize(data):
            if not data: return []
            min_val, max_val = min(data), max(data)
            if max_val == min_val:
                return [0.5] * len(data)
            return [(x - min_val) / (max_val - min_val) for x in data]
        
        ax.plot(time_data, normalize(data_ph), color=to_mpl_color(COLORS["primary"]), label='pH')
        ax.plot(time_data, normalize(data_biom), color=to_mpl_color(COLORS["success"]), label='Cresc. Leveduras')
        ax.plot(time_data, normalize(data_sucrose), color=to_mpl_color(COLORS["warning"]), label='Sacarose')
        ax.plot(time_data, normalize(data_maltose), color='deepskyblue', label='Maltose')
        ax.plot(time_data, normalize(data_volume), color='purple', label='Volume')
        ax.plot(time_data, normalize(data_co2), color=to_mpl_color(COLORS["error"]), label='CO₂')
        ax.plot(time_data, normalize(data_etoh), color='brown', label='Etanol') 
        
        ax.set_title("Evolução Normalizada da Fermentação")
        
        ax.set_xlabel("Tempo (min)")
        ax.set_ylabel("Progresso Normalizado (0 a 1)")
        ax.grid(True, linestyle="--", alpha=0.7)
        ax.legend(fontsize='small')
        
        plt.tight_layout()
        canvas = FigureCanvas(fig)
        canvas.draw()
        raw = canvas.buffer_rgba()
        raw_bytes = raw.tobytes()
        size = canvas.get_width_height()
        plt.close(fig)
        
        graph = pygame.image.frombuffer(raw_bytes, size, "RGBA")
        report_surface.blit(graph, (510, 90))
    
    # Botão para voltar
    back_button = ImprovedButton(WIDTH//2 - 75, HEIGHT - 60, 150, 40, "Voltar", COLORS["primary"])
    back_button.draw(report_surface)
    
    return report_surface, back_button


def wrap_text(text, font, max_width):
    """Divide um texto em várias linhas que caibam na largura especificada"""
    words = text.split(" ")
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + word + " "
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word + " "
    lines.append(current_line)
    return lines


def handle_config(events, mouse_pos):
    """Handles configuration screen."""
    global state, running_simulation, paused, active_slider

    title = "Configuração da Simulação"
    
    screen.blit(TITLE_FONT.render(title, True, COLORS["text"]), (40, 36))
    
    # --- Atualiza e Desenha Sliders ---
    for s in sliders:
        s.draw(screen)
    for s in sliders:
        s.update(mouse_pos)
        
    start_button.draw(screen)
    
    # --- LÓGICA DO PAINEL DE PREVISÃO ---
    # 1. Pega os valores atuais dos sliders
    current_params = [s.value for s in sliders]
    
    # 2. Calcula a previsão
    prediction = get_prediction_feedback(current_params)
    
    # 3. Desenha o painel (à direita da tela)
    draw_prediction_panel(screen, 420, 100, 760, 220, prediction)
    
    # --- Lógica dos botões e sliders ---
    if start_button.update(mouse_pos, events):
        reset_simulation()
        running_simulation = True
        paused = False
        state = screen_manager.go_to("simulacao")
        tutorial_system.show_tip("simulation_running", "A simulação está rodando! Observe os gráficos e a visualização.")

    for event in events:
        if event.type == pygame.MOUSEBUTTONDOWN:
            for s in sliders:
                if s.start_drag(mouse_pos):
                    active_slider = s; break
        elif event.type == pygame.MOUSEMOTION and active_slider:
            # A previsão é atualizada automaticamente no início do loop
            if active_slider:
                active_slider.move(mouse_pos)
        elif event.type == pygame.MOUSEBUTTONUP:
            if active_slider: active_slider.stop_drag()
            active_slider = None

def handle_simulation(events, mouse_pos):
    """Handles the running simulation screen."""
    global state, running_simulation, paused, sim_time, result_screen, result_back_button, simulation_speed, simulation_finished

    time_limit = sliders[-1].value # Último slider é o Tempo

    # --- Lógica de atualização da simulação ---
    if running_simulation and not paused:
        sim_time += simulation_speed
        
        params = [s.value for s in sliders]
        biom, suc, malt, co2v, vol, phv, etoh, ret = update_simulation(sim_time, params[2], params[3], params[1], params[0], params[4])
        
        data_biom.append(biom)
        data_sucrose.append(suc)
        data_maltose.append(malt)
        data_gluten_retention.append(ret)
        data_co2.append(co2v)
        data_volume.append(vol); data_ph.append(phv); data_etoh.append(etoh)
        
        time_data.append(sim_time)
        if int(sim_time) % 12 == 0: add_bubble()
        update_bubbles()

        if sim_time >= time_limit:
            sim_time = time_limit 
            running_simulation = False
            paused = True 
            simulation_finished = True 

    # --- Lógica de Renderização ---
    progress = min(1.0, sim_time / time_limit) if time_limit > 0 else 0.0
    graph_surf = create_improved_graphs()
    screen.blit(graph_surf, (420, 30))
    draw_educational_visual(progress)
    
    # --- Lógica de Botões ---
    
    if simulation_finished:
        # 1. Desenha o aviso por cima de tudo
        draw_finish_notice(screen)
        
        # 2. Desenha o botão de Relatório e o de Voltar
        ver_relatorio_button.draw(screen)
        voltar_button.draw(screen)

        # 3. Lida com os cliques desses botões
        if ver_relatorio_button.update(mouse_pos, events):
            result_screen, result_back_button = create_educational_report()
            state = "resultados"
            simulation_finished = False 
        
        if voltar_button.update(mouse_pos, events):
            reset_simulation()
            state = "config"
            
    else:
        # --- Se a simulação NÃO terminou, desenha os controles normais ---
        start_button.draw(screen); pause_button.draw(screen); reset_button.draw(screen); voltar_button.draw(screen)
        speed_1x_button.draw(screen); speed_2x_button.draw(screen); speed_5x_button.draw(screen)

        # Lógica de update dos botões normais
        if start_button.update(mouse_pos, events):
            if not running_simulation: # Se estava parada no início
                running_simulation = True
            paused = False
        
        if pause_button.update(mouse_pos, events):
            if running_simulation: paused = not paused
        
        if reset_button.update(mouse_pos, events):
            reset_simulation()
        
        if voltar_button.update(mouse_pos, events):
            reset_simulation()
            state = "config"
        
        # Lógica dos botões de velocidade
        if speed_1x_button.update(mouse_pos, events):
            simulation_speed = 1.0
        if speed_2x_button.update(mouse_pos, events):
            simulation_speed = 2.0
        if speed_5x_button.update(mouse_pos, events):
            simulation_speed = 5.0


def handle_resultados(events, mouse_pos):
    """Handles the results screen."""
    global state

    if result_screen:
        screen.blit(result_screen, (0, 0))
        if result_back_button and result_back_button.update(mouse_pos, events):
            state = "config" # Volta para a tela de config
            reset_simulation()

# --------- Inicializar sistemas ----------
screen_manager = ScreenManager()
tutorial_system = TutorialSystem()

# --------- Loop principal ----------
clock = pygame.time.Clock()
running = True
result_screen = None
result_back_button = None

# Inicia o tutorial na tela de configuração
tutorial_system.show_tip("adjust_params", "Ajuste os parâmetros (Farinha, Água, Sal, etc.) e clique 'Start' para simular!")

while running:
    screen.fill(COLORS["background"])
    events = pygame.event.get()
    mouse_pos = pygame.mouse.get_pos()
    mensagem_debug = time_data[-1] if time_data else 0

    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_d:  # Tecla D para toggle debug
                show_debug = not show_debug
        if event.type == pygame.QUIT:
            running = False

    # Atualizar sistemas
    tutorial_system.update()

    # --------- Renderização ----------
    if state == "config":
        handle_config(events, mouse_pos)
    elif state == "simulacao":
        handle_simulation(events, mouse_pos)
    elif state == "resultados":
        handle_resultados(events, mouse_pos)

    # Desenhar dicas do tutorial
    tutorial_system.draw(screen)
    
    # Debug Information
    if show_debug:
        debug_text(f"Estado: {state}", 10, 10)
        debug_text(f"Mouse: {mouse_pos}", 10, 30)
        debug_text(f"Tempo: {sim_time:.1f}", 10, 50)
        debug_text(f"Running: {running_simulation}", 10, 70)
        debug_text(f"Paused: {paused}", 10, 90)
        debug_text(f"FPS: {clock.get_fps():.1f}", 10, 110)
        debug_text(f"Active Slider: {active_slider}", 10, 130)
        debug_text(f"Mensagem: {mensagem_debug}", 10, 150)

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
sys.exit()