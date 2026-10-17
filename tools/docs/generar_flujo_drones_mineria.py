#!/usr/bin/env python3
"""
Documento PDF: Flujo de Trabajo Completo - Simulación y Diseño de Enjambre de Drones para Minería
"""

from datetime import datetime
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Colores
PRIMARY = HexColor("#1a365d")
SECONDARY = HexColor("#2b6cb0")
ACCENT = HexColor("#ed8936")
LIGHT_BG = HexColor("#ebf8ff")
DARK_TEXT = HexColor("#1a202c")
GRAY = HexColor("#4a5568")
SUCCESS = HexColor("#276749")
TABLE_HEADER = HexColor("#2c5282")
TABLE_ALT = HexColor("#ebf8ff")

def create_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="CoverTitle",
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=28,
        alignment=TA_CENTER,
        textColor=PRIMARY,
        spaceAfter=12
    ))
    styles.add(ParagraphStyle(
        name="CoverSubtitle",
        fontName="Helvetica",
        fontSize=13,
        leading=18,
        alignment=TA_CENTER,
        textColor=GRAY,
        spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        name="SectionTitle",
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=PRIMARY,
        spaceBefore=16,
        spaceAfter=8,
        borderPadding=3
    ))
    styles.add(ParagraphStyle(
        name="SubSection",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=SECONDARY,
        spaceBefore=10,
        spaceAfter=5
    ))
    styles.add(ParagraphStyle(
        name="BodyText2",
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        alignment=TA_JUSTIFY,
        textColor=DARK_TEXT,
        spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name="BulletText",
        fontName="Helvetica",
        fontSize=9.5,
        leading=12.5,
        textColor=DARK_TEXT,
        leftIndent=10,
        spaceAfter=3
    ))
    styles.add(ParagraphStyle(
        name="TableCell",
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=DARK_TEXT
    ))
    styles.add(ParagraphStyle(
        name="TableHeader",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=white,
        alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        name="Footer",
        fontName="Helvetica",
        fontSize=8,
        textColor=GRAY,
        alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        name="Highlight",
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13,
        textColor=SUCCESS,
        spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name="Note",
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=12,
        textColor=GRAY,
        leftIndent=8,
        spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name="TOCEntry",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=DARK_TEXT,
        spaceAfter=4
    ))
    return styles


def make_table(data, col_widths, styles):
    """Crea una tabla con estilo profesional."""
    # Convertir strings a Paragraphs para wrap
    processed = []
    for i, row in enumerate(data):
        processed_row = []
        for cell in row:
            if i == 0:
                processed_row.append(Paragraph(str(cell), styles["TableHeader"]))
            else:
                processed_row.append(Paragraph(str(cell), styles["TableCell"]))
        processed.append(processed_row)

    t = Table(processed, colWidths=col_widths, repeatRows=1)
    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#a0aec0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, TABLE_ALT]),
    ]
    t.setStyle(TableStyle(style_commands))
    return t


def add_header_footer(canvas, doc):
    canvas.saveState()
    # Header line
    canvas.setStrokeColor(PRIMARY)
    canvas.setLineWidth(1.5)
    canvas.line(1.5*cm, A4[1] - 1.2*cm, A4[0] - 1.5*cm, A4[1] - 1.2*cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GRAY)
    canvas.drawString(1.5*cm, A4[1] - 1.0*cm, "Enjambre de Drones para Minería — Flujo de Trabajo Completo")
    # Footer
    canvas.setLineWidth(0.5)
    canvas.line(1.5*cm, 1.3*cm, A4[0] - 1.5*cm, 1.3*cm)
    canvas.drawCentredString(A4[0]/2, 0.8*cm, f"Página {doc.page}")
    canvas.restoreState()


def build_document():
    styles = create_styles()
    story = []

    # ========== PORTADA ==========
    story.append(Spacer(1, 2.5*cm))
    story.append(Paragraph("FLUJO DE TRABAJO COMPLETO", styles["CoverTitle"]))
    story.append(Paragraph("Simulación, Diseño e Ingeniería de un<br/>Enjambre de Drones para Operaciones Mineras", styles["CoverTitle"]))
    story.append(Spacer(1, 0.6*cm))
    story.append(HRFlowable(width="80%", thickness=2, color=ACCENT, spaceBefore=5, spaceAfter=5, hAlign="CENTER"))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph("Inspección · Delivery · Control de Enjambre · Cálculos de Ingeniería", styles["CoverSubtitle"]))
    story.append(Spacer(1, 1.2*cm))

    info_data = [
        [Paragraph("<b>Objetivo</b>", styles["TableCell"]),
         Paragraph("Diseñar, simular y validar una flota de drones (inspección + carga/delivery) para zonas mineras, con base en cálculos de ingeniería y simulación realista, orientado a fabricación.", styles["TableCell"])],
        [Paragraph("<b>Alcance</b>", styles["TableCell"]),
         Paragraph("Física de vuelo, enjambre, control por app, cálculos de motores/hélices/batería, CAD paramétrico (OpenSCAD + FreeCAD), factores de seguridad, y paso a visualización fotorealista.", styles["TableCell"])],
        [Paragraph("<b>Fecha</b>", styles["TableCell"]),
         Paragraph(datetime.now().strftime("%d de %B de %Y"), styles["TableCell"])],
    ]
    info_table = Table(info_data, colWidths=[3.2*cm, 12.5*cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#90cdf4")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(info_table)
    story.append(PageBreak())

    # ========== ÍNDICE ==========
    story.append(Paragraph("1. Índice de Contenidos", styles["SectionTitle"]))
    toc = [
        "2. Contexto y Objetivo del Proyecto",
        "3. Oportunidad de Mercado en Minería",
        "4. Arquitectura General del Sistema",
        "5. Frameworks y Herramientas Seleccionadas",
        "6. Comparación XTDrone vs AirSim + Unreal Engine",
        "7. Flujo de Trabajo Completo (Pipeline)",
        "8. Variables de Ingeniería y Cálculos",
        "9. Factores de Seguridad",
        "10. Diseño de Hélices y Motores",
        "11. Personalización de CAD y Modelos 3D",
        "12. Simulación de Enjambre (Colmena)",
        "13. Física: Viento, Obstáculos y Control",
        "14. Portabilidad de Algoritmos entre Simuladores",
        "15. Repositorios Open Source Relevantes",
        "16. Resumen de Decisiones y Próximos Pasos",
    ]
    for item in toc:
        story.append(Paragraph(item, styles["TOCEntry"]))
    story.append(PageBreak())

    # ========== 2. CONTEXTO ==========
    story.append(Paragraph("2. Contexto y Objetivo del Proyecto", styles["SectionTitle"]))
    story.append(Paragraph(
        "El proyecto busca crear una simulación ultra-realista de un <b>enjambre de drones</b> orientado a "
        "operaciones mineras, con dos tipos de vehículos: (1) drones de <b>inspección</b> y (2) drones de "
        "<b>carga / delivery</b>. El objetivo final es realizar todos los cálculos de ingeniería necesarios "
        "para poder <b>fabricar una flota real</b>.",
        styles["BodyText2"]
    ))
    story.append(Paragraph("Historias de usuario principales:", styles["SubSection"]))
    story.append(Paragraph("• Inspección de taludes, conveyors, idlers, relaves, post-blast e infraestructura.", styles["BulletText"]))
    story.append(Paragraph("• Delivery de herramientas, repuestos, muestras geológicas y suministros en minas abiertas o subterráneas.", styles["BulletText"]))
    story.append(Paragraph("• Control colectivo del enjambre desde una aplicación.", styles["BulletText"]))
    story.append(Paragraph("• Validación de física de vuelo, viento, obstáculos y fallos antes de fabricar.", styles["BulletText"]))

    # ========== 3. MERCADO ==========
    story.append(Paragraph("3. Oportunidad de Mercado en Minería", styles["SectionTitle"]))
    story.append(Paragraph(
        "El mercado global de drones/servicios para minería se estima entre <b>USD 1.8 – 4.8 mil millones en 2025</b>, "
        "con proyecciones de alcanzar <b>USD 6 – 11 mil millones hacia 2032–2034</b> (CAGR 12–16%). "
        "Casos reales (DJI Dock en Rio Tinto Gudai-Darri y Anglo American Quellaveco) demuestran 150–200 vuelos/mes "
        "por dock, reducción de tiempo de surveys post-blast de 1.2 h a 30 min, y operación remota vía Starlink.",
        styles["BodyText2"]
    ))
    story.append(Paragraph("Propuesta de valor:", styles["SubSection"]))
    story.append(Paragraph("• Menor exposición de personal a zonas de riesgo.", styles["BulletText"]))
    story.append(Paragraph("• Datos más frecuentes y precisos para decisión operativa.", styles["BulletText"]))
    story.append(Paragraph("• Delivery rápido de piezas/herramientas → menos downtime.", styles["BulletText"]))
    story.append(Paragraph("• Modelos de negocio: venta de flota + software, servicio por vuelo/mes, o drone-as-a-service.", styles["BulletText"]))

    # ========== 4. ARQUITECTURA ==========
    story.append(Paragraph("4. Arquitectura General del Sistema", styles["SectionTitle"]))
    story.append(Paragraph(
        "La arquitectura típica separa la aplicación de control, el servidor de orquestación y el simulador (o el hardware real):",
        styles["BodyText2"]
    ))
    arch = [
        ["Capa", "Componentes", "Función"],
        ["App de control", "Flutter / React Native / Web", "Interfaz de operador, misiones, telemetría"],
        ["Comunicación", "WebSocket / gRPC / MQTT / MAVLink", "Comandos y telemetría en tiempo real"],
        ["Servidor de control", "Python / C++ / ROS2", "Orquestación de enjambre, planificación"],
        ["Simulador / Hardware", "XTDrone (Gazebo+PX4) o AirSim+PX4 o drones reales", "Física, sensores, motores"],
        ["Autopiloto", "PX4 (SITL o real)", "Control de bajo nivel (actitud, posición)"],
    ]
    story.append(make_table(arch, [3.5*cm, 5.5*cm, 7*cm], styles))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "Cada drone modela 6 grados de libertad, controladores en cascada (posición → velocidad → actitud → motores), "
        "sensores con ruido, modelo de batería y comunicaciones con latencia.",
        styles["BodyText2"]
    ))
    story.append(PageBreak())

    # ========== 5. FRAMEWORKS ==========
    story.append(Paragraph("5. Frameworks y Herramientas Seleccionadas", styles["SectionTitle"]))

    story.append(Paragraph("5.1 Simulación principal: XTDrone / XTDrone2", styles["SubSection"]))
    story.append(Paragraph(
        "Plataforma open source basada en <b>PX4 + ROS/ROS2 + Gazebo</b>. Soporta multi-rotor, fixed-wing, VTOL, "
        "enjambre (formaciones 6/9/18 drones), viento, obstáculos y paso relativamente directo a hardware real. "
        "XTDrone v1 es más maduro en formaciones; XTDrone2 usa ROS2 y Gazebo Ignition.",
        styles["BodyText2"]
    ))

    story.append(Paragraph("5.2 Visualización y visión: AirSim + Unreal Engine", styles["SubSection"]))
    story.append(Paragraph(
        "Simulador fotorealista sobre Unreal Engine. Ideal para demos de cliente y entrenamiento de visión artificial. "
        "Soporta PX4 SITL/HITL. El algoritmo de alto nivel desarrollado contra PX4 en XTDrone es portable a AirSim.",
        styles["BodyText2"]
    ))

    story.append(Paragraph("5.3 Diseño mecánico: OpenSCAD + FreeCAD", styles["SubSection"]))
    story.append(Paragraph(
        "<b>OpenSCAD</b> (open source, GPL): diseño paramétrico por código. Ideal para frames modulares y para agentes de IA "
        "(todo son variables en un archivo de texto). Incluye visor propio (Preview F5 / Render F6). "
        "No tiene Assembly con constraints; el ensamble se hace por módulos y transformaciones, o después en FreeCAD/XTDrone.",
        styles["BodyText2"]
    ))
    story.append(Paragraph(
        "<b>FreeCAD</b> (open source): visualización de STL, ensambles más elaborados, ajustes finos y preparación de exports. "
        "Flujo típico: diseñar paramétrico en OpenSCAD → exportar STL → revisar/ensamblar en FreeCAD → exportar mallas para XTDrone (SDF) y AirSim.",
        styles["BodyText2"]
    ))
    story.append(Paragraph(
        "Bases CAD open source recomendadas: frames paramétricos FreeCAD, devFrame (STEP/STL), MFPV (modular delivery), "
        "y varios frames OpenSCAD (H-frame, whoop, Lucy, etc.) para no partir de cero.",
        styles["BodyText2"]
    ))

    story.append(Paragraph("5.4 Cálculos de ingeniería: Python", styles["SubSection"]))
    story.append(Paragraph(
        "Numpy, SciPy, Matplotlib y modelos analíticos/semi-empíricos (empuje, potencia, batería, BEMT). "
        "Suficiente para dimensionamiento con factores de seguridad. CFD (OpenFOAM) solo si se requiere optimización extrema de hélices.",
        styles["BodyText2"]
    ))

    story.append(Paragraph("5.5 Autopiloto y comunicación", styles["SubSection"]))
    story.append(Paragraph(
        "PX4 (SITL y real), MAVLink, MAVSDK / MAVROS / px4_msgs. Garantiza que el mismo código de control "
        "funcione en simulación y en hardware.",
        styles["BodyText2"]
    ))

    # ========== 6. COMPARACIÓN ==========
    story.append(Paragraph("6. Comparación XTDrone vs AirSim + Unreal Engine", styles["SectionTitle"]))
    comp = [
        ["Aspecto", "XTDrone (Gazebo+PX4)", "AirSim + Unreal"],
        ["Física de vuelo", "Buena (Gazebo + PX4 real)", "Buena, más orientada a visual"],
        ["Realismo visual", "Medio (funcional)", "Muy alto (fotorealista)"],
        ["Soporte de enjambre", "Muy bueno (demos 6–18+)", "Posible, más trabajo manual"],
        ["Integración ROS/PX4", "Excelente (nativo)", "Buena (PX4 SITL/HITL)"],
        ["Consumo de recursos", "Bajo–Medio", "Alto (requiere buena GPU)"],
        ["Personalizar drones", "Alta (SDF + meshes)", "Media–Alta (Unreal)"],
        ["Sensores", "Buenos y fáciles", "Excelentes (cámaras)"],
        ["Viento y obstáculos", "Bueno y documentado", "Bueno"],
        ["Madurez multi-drone", "Más maduro", "Más orientado a visión/IA"],
        ["Curva de aprendizaje", "Media", "Más alta"],
    ]
    story.append(make_table(comp, [3.8*cm, 6.2*cm, 6*cm], styles))
    story.append(Spacer(1, 0.25*cm))
    story.append(Paragraph(
        "<b>Decisión:</b> XTDrone como simulador principal (control, física, enjambre, ingeniería). "
        "AirSim + Unreal para videos de cliente y aplicaciones de visión artificial.",
        styles["Highlight"]
    ))
    story.append(PageBreak())

    # ========== 7. FLUJO DE TRABAJO ==========
    story.append(Paragraph("7. Flujo de Trabajo Completo (Pipeline)", styles["SectionTitle"]))
    story.append(Paragraph(
        "El flujo adoptado es iterativo e incluye validación en simulación antes de fabricar:",
        styles["BodyText2"]
    ))

    flow = [
        ["Fase", "Herramientas", "Actividades principales", "Salidas"],
        ["1. Requisitos y misiones", "Documento / historias de usuario", "Definir inspección, delivery, enjambre, condiciones de mina", "Historias de usuario, escenarios"],
        ["2. Simulación de misiones", "XTDrone", "Ejecutar tareas, viento, obstáculos, formación", "Logs: empuje, torque, corriente, tiempo de vuelo"],
        ["3. Cálculos de ingeniería", "Python", "Dimensionar empuje, motores, hélices, batería con factores de seguridad", "Especificaciones de componentes"],
        ["4. Diseño mecánico", "OpenSCAD + FreeCAD (+ XTDrone)", "Frame paramétrico, chasis, montajes, carga; importar a sim", "Modelo CAD + SDF validado"],
        ["5. Validación dinámica", "XTDrone", "Probar diseño con carga, viento, enjambre; ajustar", "Diseño estable"],
        ["6. Visualización / visión", "AirSim + Unreal", "Demos para cliente, datasets de visión", "Videos, modelos de detección"],
        ["7. Hardware real", "PX4 + flota física", "Portar algoritmo (MAVLink/MAVSDK), pruebas de campo", "Flota operativa"],
    ]
    story.append(make_table(flow, [2.8*cm, 3.5*cm, 5.5*cm, 4.2*cm], styles))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "Enfoque “de la misión hacia el hardware” (iterativo): se simulan las tareas, se extraen variables "
        "(empuje, potencia, etc.), se dimensiona el hardware, se actualiza el modelo y se vuelve a simular.",
        styles["BodyText2"]
    ))

    # ========== 8. VARIABLES ==========
    story.append(Paragraph("8. Variables de Ingeniería y Cálculos", styles["SectionTitle"]))
    story.append(Paragraph(
        "XTDrone <b>no reemplaza</b> los cálculos de diseño iniciales; los alimenta y permite validarlos. "
        "Las variables principales se calculan en Python; la simulación aporta datos dinámicos reales de misión.",
        styles["BodyText2"]
    ))

    story.append(Paragraph("8.1 Variables que se calculan en Python (diseño)", styles["SubSection"]))
    calc_vars = [
        ["Variable", "Descripción", "Uso"],
        ["Peso total (MTOW)", "Estructura + batería + carga útil + margen", "Base de todo el dimensionamiento"],
        ["Empuje total requerido", "Típicamente 1.8–2.5 × peso", "Selección de motores + hélices"],
        ["Empuje por motor", "Empuje total / N motores", "Especificación por motor"],
        ["Diámetro y paso de hélice", "Según empuje y RPM deseadas", "Selección o diseño de hélice"],
        ["KV y corriente de motor", "Según hélice y tensión de batería", "Selección de motor y ESC"],
        ["Capacidad de batería (Wh)", "Según potencia media y autonomía", "Autonomía y peso de batería"],
        ["Tiempo de vuelo estimado", "Energía / potencia media", "Requisito operativo"],
        ["Inercias y CG", "Distribución de masas", "Estabilidad y control"],
    ]
    story.append(make_table(calc_vars, [4*cm, 6.5*cm, 5.5*cm], styles))
    story.append(Spacer(1, 0.25*cm))

    story.append(Paragraph("8.2 Variables que aporta XTDrone (validación dinámica)", styles["SubSection"]))
    sim_vars = [
        ["Variable de simulación", "Para qué sirve en ingeniería"],
        ["Consumo real de corriente con carga", "Ajustar batería y verificar que el motor no se satura"],
        ["Empuje efectivo vs peso en misión", "Verificar margen de empuje real"],
        ["Estabilidad con carga descentrada", "Validar ubicación del centro de gravedad"],
        ["Respuesta al viento", "Decidir si hace falta más empuje o mejor control"],
        ["Tiempo de vuelo bajo misión real", "Contrastar con el cálculo teórico de autonomía"],
        ["Aceleraciones y maniobras", "Ajustar inercias y margen de control"],
        ["Ganancias PID / comportamiento Offboard", "Afinar el control antes del hardware"],
        ["Comportamiento en formación + obstáculos", "Validar el enjambre con carga"],
    ]
    story.append(make_table(sim_vars, [7*cm, 9*cm], styles))
    story.append(Spacer(1, 0.25*cm))

    story.append(Paragraph("8.3 Modelo simplificado de empuje en simulación (Gazebo/PX4)", styles["SubSection"]))
    story.append(Paragraph(
        "El simulador no resuelve CFD. Usa modelos empíricos del tipo:",
        styles["BodyText2"]
    ))
    story.append(Paragraph(
        "T = C<sub>T</sub> · ρ · ω² · D⁴ &nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp; Q = C<sub>Q</sub> · ρ · ω² · D⁵",
        styles["Highlight"]
    ))
    story.append(Paragraph(
        "donde ω es la velocidad angular, D el diámetro, ρ la densidad del aire, y C<sub>T</sub>, C<sub>Q</sub> "
        "coeficientes configurables. Suficiente para control y validación; el dimensionamiento fino se hace en Python.",
        styles["BodyText2"]
    ))
    story.append(PageBreak())

    # ========== 9. FACTORES DE SEGURIDAD ==========
    story.append(Paragraph("9. Factores de Seguridad", styles["SectionTitle"]))
    story.append(Paragraph(
        "Se dimensiona en Python con márgenes conservadores y luego se valida en XTDrone:",
        styles["BodyText2"]
    ))
    sf = [
        ["Variable", "Factor de seguridad típico", "Motivo"],
        ["Empuje total", "1.8 – 2.5 × peso", "Maniobras, viento, no volar al límite"],
        ["Corriente del motor", "1.3 – 1.5 × calculada", "Evitar saturación y sobrecalentamiento"],
        ["Capacidad de batería", "1.3 – 1.5 × necesaria", "Envejecimiento, frío, descargas no ideales"],
        ["Estructura / brazos", "2.0 – 3.0 × carga máxima", "Impactos, vibraciones, fatiga"],
        ["ESC", "1.3 – 1.5 × corriente máx. motor", "Margen térmico"],
        ["Tiempo de vuelo", "Diseñar 20–30% por encima del mínimo", "Margen operativo real"],
    ]
    story.append(make_table(sf, [4.5*cm, 5*cm, 6.5*cm], styles))
    story.append(Spacer(1, 0.25*cm))
    story.append(Paragraph(
        "Ejemplo: drone + carga = 2.0 kg → con factor 2.0 se requieren 4.0 kg de empuje total → "
        "1.0 kg por motor en un quadrotor (mínimo de diseño).",
        styles["Note"]
    ))

    # ========== 10. HÉLICES Y MOTORES ==========
    story.append(Paragraph("10. Diseño de Hélices y Motores", styles["SectionTitle"]))
    story.append(Paragraph("10.1 Enfoque recomendado: hélices comerciales", styles["SubSection"]))
    story.append(Paragraph(
        "Para la gran mayoría de proyectos (incluido este) se seleccionan hélices comerciales (APC, Gemfan, T-Motor, HQProp, etc.) "
        "con datos reales de empuje vs RPM. Python calcula la combinación motor+hélice que cumple el empuje con margen "
        "a un régimen razonable (p. ej. 70–80% throttle).",
        styles["BodyText2"]
    ))
    story.append(Paragraph("Leyes de escala aproximadas al cambiar diámetro (mismas RPM):", styles["BodyText2"]))
    story.append(Paragraph("• +10% diámetro → ~+21% empuje", styles["BulletText"]))
    story.append(Paragraph("• +20% diámetro → ~+44% empuje", styles["BulletText"]))
    story.append(Paragraph("• Más diámetro → más empuje y más torque; menos RPM máximas posibles.", styles["BulletText"]))

    story.append(Paragraph("10.2 Diseño propio de hélices (avanzado)", styles["SubSection"]))
    story.append(Paragraph(
        "Solo si se necesita optimización extrema (eficiencia, ruido, condiciones especiales). "
        "Se usa <b>Blade Element Momentum Theory (BEMT)</b> en Python: diámetro, número de palas, distribución de cuerda y torsión, "
        "perfil aerodinámico. Opcionalmente se valida con CFD (OpenFOAM). Para minería, el camino comercial + Python es el prioritario.",
        styles["BodyText2"]
    ))

    # ========== 11. CAD ==========
    story.append(Paragraph("11. Personalización de CAD y Modelos 3D", styles["SectionTitle"]))
    story.append(Paragraph(
        "XTDrone y AirSim <b>no entregan CAD de ingeniería</b> (STEP/SolidWorks). Entregan modelos de simulación "
        "(SDF + mallas STL/DAE en Gazebo; assets de Unreal en AirSim). El flujo correcto es:",
        styles["BodyText2"]
    ))
    story.append(Paragraph("1. Diseñar de forma <b>paramétrica</b> en <b>OpenSCAD</b> (variables: motor spacing, arm width, stack height, battery/payload bay). Opcional: partir de frames open source (devFrame, MFPV, H-frame, etc.).", styles["BulletText"]))
    story.append(Paragraph("2. Exportar STL desde OpenSCAD. Revisar / ensamblar en <b>FreeCAD</b> si hace falta.", styles["BulletText"]))
    story.append(Paragraph("3. En XTDrone: crear/modificar SDF (links, joints, masa, inercias, sensores, plugins de motor). El ensamble dinámico que vuela se define aquí.", styles["BulletText"]))
    story.append(Paragraph("4. En AirSim: importar como Static Mesh y armar Blueprint del vehículo.", styles["BulletText"]))
    story.append(Paragraph("5. Configurar parámetros físicos (C_T, C_Q, masa, inercias) en cada simulador por separado.", styles["BulletText"]))
    story.append(Paragraph(
        "OpenSCAD no tiene Assembly con constraints; el “ensamble” en diseño es por módulos/transformaciones. "
        "El ensamble de simulación (el que importa para vuelo) se hace en el SDF de XTDrone. "
        "El aspecto visual se puede compartir; la física debe calibrarse en cada plataforma.",
        styles["BodyText2"]
    ))
    story.append(PageBreak())

    # ========== 12. ENJAMBRE ==========
    story.append(Paragraph("12. Simulación de Enjambre (Colmena)", styles["SectionTitle"]))
    story.append(Paragraph(
        "Tanto XTDrone v1 como XTDrone2 permiten múltiples drones y comportamiento de formación:",
        styles["BodyText2"]
    ))
    swarm = [
        ["Característica", "XTDrone v1", "XTDrone2"],
        ["Agregar más drones", "Sí", "Sí"],
        ["Cantidad práctica", "6, 9, 18 (oficiales); demos hasta ~20", "Multi-vehículo (ej. 4+); escala según PC"],
        ["Formación / colmena", "Leader-follower + consensus", "Soportado (namespaces)"],
        ["Cambio de formaciones", "Sí (T, diamante, triángulo, cubo…)", "Posible (implementar/adaptar)"],
        ["Evitar colisiones", "Sí (en demos de formación)", "Se puede agregar"],
        ["Facilidad de escalar", "Buena (generador de launch)", "Buena (loop + YAML)"],
    ]
    story.append(make_table(swarm, [4*cm, 6*cm, 6*cm], styles))
    story.append(Spacer(1, 0.25*cm))
    story.append(Paragraph(
        "La comunicación entre drones en simulación es ideal (sin latencia ni pérdida de paquetes de fábrica). "
        "La cantidad de drones está limitada por la CPU/RAM del equipo.",
        styles["Note"]
    ))

    # ========== 13. FÍSICA ==========
    story.append(Paragraph("13. Física: Viento, Obstáculos y Control", styles["SectionTitle"]))
    story.append(Paragraph(
        "XTDrone permite simular control realista con viento y obstáculos:",
        styles["BodyText2"]
    ))
    story.append(Paragraph("• <b>Viento:</b> plugin de Gazebo configurable (dirección, velocidad, turbulencia, ráfagas). En v1.13 se puede cambiar en tiempo real vía ROS.", styles["BulletText"]))
    story.append(Paragraph("• <b>Obstáculos:</b> estáticos en el mundo Gazebo; sensores (LiDAR, cámaras); demos de obstacle avoidance en formaciones.", styles["BulletText"]))
    story.append(Paragraph("• <b>Control:</b> PX4 real (SITL) → comportamiento del controlador muy cercano al hardware.", styles["BulletText"]))
    phys = [
        ["Aspecto", "Nivel de realismo", "Comentario"],
        ["Viento constante", "Bueno", "Fácil de configurar"],
        ["Ráfagas / turbulencia", "Medio–Bueno", "Configurable; no es CFD completo"],
        ["Obstáculos estáticos", "Muy bueno", "Totalmente personalizable"],
        ["Obstáculos dinámicos", "Medio", "Posible con más trabajo"],
        ["Aerodinámica detallada", "Media", "LiftDrag + motor model; no CFD"],
        ["Control realista", "Bueno", "PX4 SITL"],
    ]
    story.append(make_table(phys, [4.5*cm, 3.5*cm, 8*cm], styles))

    # ========== 14. PORTABILIDAD ==========
    story.append(Paragraph("14. Portabilidad de Algoritmos entre Simuladores", styles["SectionTitle"]))
    story.append(Paragraph(
        "Si el algoritmo se desarrolla <b>hablando con PX4</b> (MAVSDK, MAVROS, px4_msgs, setpoints Offboard), "
        "la mayor parte es portable de XTDrone a AirSim y luego al hardware real:",
        styles["BodyText2"]
    ))
    port = [
        ["Tipo de algoritmo", "¿Portable a AirSim?", "Notas"],
        ["Control de enjambre (formación, consensus)", "Sí", "Vía MAVLink/MAVSDK/ROS + PX4 Offboard"],
        ["Planificación de trayectorias", "Sí", "Waypoints/setpoints a PX4"],
        ["Lógica de misiones (inspección, delivery)", "Sí", "Código de alto nivel"],
        ["Visión (detección, tracking)", "Parcialmente", "Adaptar fuente de imágenes"],
        ["Plugins específicos de Gazebo", "No", "Dependientes del simulador"],
    ]
    story.append(make_table(port, [5.5*cm, 3.5*cm, 7*cm], styles))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "CAD/visuales: reutilizables con conversión de mallas. Parámetros físicos de motores/hélices: "
        "configurar de nuevo en cada simulador.",
        styles["Note"]
    ))
    story.append(PageBreak())

    # ========== 15. REPOS ==========
    story.append(Paragraph("15. Repositorios Open Source Relevantes", styles["SectionTitle"]))
    repos = [
        ["Repo", "Aporte principal", "Personalización", "Info para ingeniería"],
        ["XTDrone / XTDrone2", "Simulación PX4+ROS+Gazebo, multi-UAV, formaciones", "Alta", "Media–Alta"],
        ["Prometheus", "Control, planning, detección, swarm", "Alta", "Media"],
        ["PX4_Swarm_Controller", "Formación leader-follower ROS2+Gazebo", "Media–Alta", "Baja–Media"],
        ["mavsdk_drone_show (MDS)", "Operaciones de flota, misiones, dashboard", "Media", "Baja"],
        ["FastSwarmSim", "Sim multi-UAV ligero PX4+ROS2", "Media", "Baja"],
        ["Project-Flockwork", "Control descentralizado desde cero", "Media", "Baja–Media"],
        ["AirSim (+ forks)", "Visual fotorealista, PX4, sensores", "Media", "Media"],
    ]
    story.append(make_table(repos, [4*cm, 5*cm, 3.2*cm, 3.8*cm], styles))
    story.append(Spacer(1, 0.25*cm))
    story.append(Paragraph(
        "Recomendación de stack: XTDrone como base; PX4 + MAVSDK/MAVROS; <b>OpenSCAD</b> (diseño paramétrico) + "
        "<b>FreeCAD</b> (visualización/ensamble); Python para cálculos; AirSim cuando se necesite visualización o visión de alta fidelidad.",
        styles["BodyText2"]
    ))

    # ========== 16. RESUMEN ==========
    story.append(Paragraph("16. Resumen de Decisiones y Próximos Pasos", styles["SectionTitle"]))
    story.append(Paragraph("Decisiones tomadas:", styles["SubSection"]))
    story.append(Paragraph("• Simulador principal: <b>XTDrone</b> (control, física, enjambre, variables de ingeniería).", styles["BulletText"]))
    story.append(Paragraph("• Visualización / visión / demos: <b>AirSim + Unreal</b>.", styles["BulletText"]))
    story.append(Paragraph("• Cálculos de ingeniería: <b>Python</b> con factores de seguridad (no se queda corto para dimensionamiento).", styles["BulletText"]))
    story.append(Paragraph("• Diseño mecánico: <b>OpenSCAD</b> (paramétrico, amigable para IA) + <b>FreeCAD</b> (visualización/ensamble) → importación a XTDrone y AirSim.", styles["BulletText"]))
    story.append(Paragraph("• Hélices: prioritariamente <b>comerciales</b> + cálculo en Python; BEMT solo si se requiere custom.", styles["BulletText"]))
    story.append(Paragraph("• Autopiloto y portabilidad: <b>PX4</b> + interfaces estándar (MAVLink/MAVSDK/ROS).", styles["BulletText"]))
    story.append(Paragraph("• Flujo: misión en XTDrone → variables → cálculos Python → OpenSCAD/FreeCAD + iteración XTDrone → AirSim para cliente/visión → hardware.", styles["BulletText"]))

    story.append(Paragraph("Próximos pasos sugeridos:", styles["SubSection"]))
    story.append(Paragraph("1. Definir historias de usuario y misiones concretas de mina (inspección y delivery) con pesos, autonomía y número de drones objetivo.", styles["BulletText"]))
    story.append(Paragraph("2. Montar entorno XTDrone y lanzar una formación básica (6–9 drones).", styles["BulletText"]))
    story.append(Paragraph("3. Implementar en Python la plantilla de cálculo (empuje, motores, hélices, batería) con factores de seguridad.", styles["BulletText"]))
    story.append(Paragraph("4. Ejecutar misiones de referencia, extraer logs y cerrar el primer ciclo de dimensionamiento.", styles["BulletText"]))
    story.append(Paragraph("5. Iniciar CAD paramétrico del chasis en OpenSCAD (o FreeCAD), exportar STL e importarlo a XTDrone para validación.", styles["BulletText"]))

    story.append(Spacer(1, 0.6*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=5, spaceAfter=8))
    story.append(Paragraph(
        "Documento generado como síntesis del flujo de trabajo acordado para el diseño y simulación "
        "de un enjambre de drones de inspección y delivery en entornos mineros. "
        "Sirve como referencia de arquitectura, herramientas, variables de ingeniería y secuencia de trabajo.",
        styles["Note"]
    ))

    # Build PDF
    output_path = str(Path(__file__).resolve().parents[2] / "docs" / "flujo" / "Flujo_Trabajo_Enjambre_Drones_Mineria.pdf")
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm,
        topMargin=1.6*cm,
        bottomMargin=1.6*cm,
        title="Flujo de Trabajo — Enjambre de Drones para Minería",
        author="Equipo DronSwarm",
    )
    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    print(f"PDF generado: {output_path}")
    return output_path


if __name__ == "__main__":
    build_document()
