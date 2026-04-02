"""DNA Helix Visualization Module — Generates SVG and programmatic DNA graphics"""

import base64
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np


def generate_dna_helix_svg():
    """Generate SVG of an animated DNA helix for web app"""
    svg = """
    <svg viewBox="0 0 350 450" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto; max-width: 400px; margin: 0 auto; display: block;">
        <defs>
            <style>
                @keyframes helixRotate {
                    0% { transform: rotateZ(0deg); }
                    100% { transform: rotateZ(360deg); }
                }
                @keyframes float {
                    0%, 100% { transform: translateY(0px); }
                    50% { transform: translateY(-10px); }
                }
                .helix-main {
                    animation: helixRotate 20s linear infinite;
                    transform-origin: center;
                }
                .helix-container {
                    animation: float 6s ease-in-out infinite;
                }
            </style>
            <linearGradient id="grad1" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:#ef4444;stop-opacity:1" />
                <stop offset="50%" style="stop-color:#f59e0b;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#3fffd2;stop-opacity:0.8" />
            </linearGradient>
            <linearGradient id="grad2" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:#8b5cf6;stop-opacity:1" />
                <stop offset="50%" style="stop-color:#0066cc;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#63d2be;stop-opacity:0.8" />
            </linearGradient>
            <filter id="glow">
                <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                </feMerge>
            </filter>
        </defs>
        
        <!-- Background -->
        <rect width="350" height="450" fill="transparent"/>
        
        <!-- Container with float animation -->
        <g class="helix-container">
            <!-- Main helix group with rotation -->
            <g class="helix-main">
                <!-- Left strand (curved) -->
                <path d="M 100 80 Q 80 180 100 280 Q 120 380 100 420" 
                      stroke="url(#grad1)" stroke-width="8" fill="none" 
                      stroke-linecap="round" opacity="0.95" filter="url(#glow)"/>
                
                <!-- Right strand (curved) -->
                <path d="M 250 80 Q 270 180 250 280 Q 230 380 250 420" 
                      stroke="url(#grad2)" stroke-width="8" fill="none" 
                      stroke-linecap="round" opacity="0.95" filter="url(#glow)"/>
                
                <!-- Base pair rungs (connecting lines) -->
                <g opacity="0.8" stroke-linecap="round">
                    <line x1="100" y1="100" x2="250" y2="100" stroke="#ef4444" stroke-width="3" filter="url(#glow)"/>
                    <line x1="98" y1="150" x2="252" y2="150" stroke="#f59e0b" stroke-width="3" filter="url(#glow)"/>
                    <line x1="95" y1="200" x2="255" y2="200" stroke="#0066cc" stroke-width="3" filter="url(#glow)"/>
                    <line x1="98" y1="250" x2="252" y2="250" stroke="#8b5cf6" stroke-width="3" filter="url(#glow)"/>
                    <line x1="100" y1="300" x2="250" y2="300" stroke="#3fffd2" stroke-width="3" filter="url(#glow)"/>
                    <line x1="102" y1="350" x2="248" y2="350" stroke="#ef4444" stroke-width="3" filter="url(#glow)"/>
                    <line x1="105" y1="400" x2="245" y2="400" stroke="#0066cc" stroke-width="3" filter="url(#glow)"/>
                </g>
                
                <!-- Base letters with colors -->
                <g font-family="'Monaco', 'Courier New', monospace" font-size="14" font-weight="bold" text-anchor="middle">
                    <text x="65" y="110" fill="#ef4444" opacity="0.8">A</text>
                    <text x="285" y="110" fill="#8b5cf6" opacity="0.8">T</text>
                    <text x="63" y="160" fill="#f59e0b" opacity="0.8">T</text>
                    <text x="287" y="160" fill="#0066cc" opacity="0.8">A</text>
                    <text x="60" y="210" fill="#0066cc" opacity="0.8">G</text>
                    <text x="290" y="210" fill="#8b5cf6" opacity="0.8">C</text>
                    <text x="62" y="260" fill="#8b5cf6" opacity="0.8">C</text>
                    <text x="288" y="260" fill="#ef4444" opacity="0.8">G</text>
                    <text x="65" y="310" fill="#3fffd2" opacity="0.8">A</text>
                    <text x="285" y="310" fill="#f59e0b" opacity="0.8">T</text>
                    <text x="68" y="360" fill="#ef4444" opacity="0.8">G</text>
                    <text x="282" y="360" fill="#0066cc" opacity="0.8">C</text>
                    <text x="70" y="410" fill="#0066cc" opacity="0.8">T</text>
                    <text x="280" y="410" fill="#8b5cf6" opacity="0.8">A</text>
                </g>
            </g>
            
            <!-- Decorative glowing circles -->
            <g opacity="0.4">
                <circle cx="175" cy="150" r="40" fill="none" stroke="#3fffd2" stroke-width="1"/>
                <circle cx="175" cy="250" r="50" fill="none" stroke="#ef4444" stroke-width="1"/>
                <circle cx="175" cy="350" r="40" fill="none" stroke="#0066cc" stroke-width="1"/>
            </g>
        </g>
    </svg>
    """
    return svg


def generate_dna_helix_matplotlib():
    """Generate DNA helix visualization using Matplotlib (for desktop app)"""
    fig, ax = plt.subplots(figsize=(5, 6), dpi=100)
    fig.patch.set_facecolor('#070b12')
    ax.set_facecolor('#0c1220')
    
    # Create helix
    t = np.linspace(0, 4*np.pi, 100)
    x1 = 2 * np.cos(t)
    y1 = t
    x2 = 2 * np.cos(t + np.pi)
    y2 = t
    
    # Plot strands
    ax.plot(x1, y1, color='#3fffd2', linewidth=3, alpha=0.8, label='Strand 1')
    ax.plot(x2, y2, color='#a78bfa', linewidth=3, alpha=0.8, label='Strand 2')
    
    # Add base pair rungs
    for i in range(0, len(t), 8):
        ax.plot([x1[i], x2[i]], [y1[i], y2[i]], color='#63d2be', linewidth=2, alpha=0.6)
    
    # Styling
    ax.set_xlim(-3, 3)
    ax.set_ylim(0, 4*np.pi)
    ax.axis('off')
    ax.set_aspect('equal')
    
    # Convert to base64
    buf = BytesIO()
    fig.savefig(buf, format='png', facecolor='#070b12', bbox_inches='tight', dpi=100)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    
    return f"data:image/png;base64,{img_base64}"


def generate_dna_pattern_viz(pattern: str) -> str:
    """Generate visualization of DNA pattern bases"""
    base_colors = {'A': '#ff6b8a', 'T': '#f5c842', 'C': '#3fffd2', 'G': '#a78bfa'}
    
    fig, ax = plt.subplots(figsize=(12, 1.5), dpi=100)
    fig.patch.set_facecolor('#070b12')
    ax.set_facecolor('#0c1220')
    
    for i, base in enumerate(pattern):
        color = base_colors.get(base, '#8fa8a0')
        rect = patches.Rectangle((i, 0), 0.9, 1, linewidth=1, 
                                edgecolor=color, facecolor=color, alpha=0.3)
        ax.add_patch(rect)
        ax.text(i + 0.45, 0.5, base, ha='center', va='center', 
               fontsize=14, fontweight='bold', color=color, 
               fontfamily='monospace')
    
    ax.set_xlim(-0.5, len(pattern))
    ax.set_ylim(0, 1)
    ax.axis('off')
    
    buf = BytesIO()
    fig.savefig(buf, format='png', facecolor='#070b12', bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    
    return f"data:image/png;base64,{img_base64}"


def generate_match_distribution_chart(matches: list, genome_length: int):
    """Generate match distribution visualization"""
    fig, ax = plt.subplots(figsize=(10, 4), dpi=100)
    fig.patch.set_facecolor('#070b12')
    ax.set_facecolor('#0c1220')
    
    if matches:
        ax.scatter(range(len(matches)), matches, color='#3fffd2', s=100, alpha=0.8, edgecolors='#63d2be', linewidth=1.5)
    
    ax.set_xlabel('Match #', color='#8fa8a0', fontfamily='monospace', fontsize=10)
    ax.set_ylabel('Position in Genome', color='#8fa8a0', fontfamily='monospace', fontsize=10)
    ax.tick_params(colors='#8fa8a0')
    ax.spines['bottom'].set_color('#63d2be')
    ax.spines['left'].set_color('#63d2be')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, alpha=0.1, color='rgba(99,210,190,0.2)')
    
    buf = BytesIO()
    fig.savefig(buf, format='png', facecolor='#070b12', bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    
    return f"data:image/png;base64,{img_base64}"

