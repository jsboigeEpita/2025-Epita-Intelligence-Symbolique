// Presentation Application JavaScript
class PresentationApp {
    constructor() {
        this.currentSlide = 0;
        this.totalSlides = 11;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.updateSlideCounter();
        this.updateNavigationButtons();
        this.initComponentInteractions();
        this.initPersonalityInteractions();
        this.initChartInteractions();
    }

    setupEventListeners() {
        // Navigation buttons
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const slideSelector = document.getElementById('slideSelector');

        prevBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.previousSlide();
        });
        nextBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.nextSlide();
        });
        slideSelector.addEventListener('change', (e) => this.goToSlide(parseInt(e.target.value)));

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                this.previousSlide();
            }
            if (e.key === 'ArrowRight') {
                e.preventDefault();
                this.nextSlide();
            }
            if (e.key === 'Escape') this.closeModal();
        });

        // Modal close
        const modal = document.getElementById('chartModal');
        const closeBtn = modal.querySelector('.close');
        closeBtn.addEventListener('click', () => this.closeModal());
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) this.closeModal();
        });
    }

    previousSlide() {
        if (this.currentSlide > 0) {
            this.goToSlide(this.currentSlide - 1);
        }
    }

    nextSlide() {
        if (this.currentSlide < this.totalSlides - 1) {
            this.goToSlide(this.currentSlide + 1);
        }
    }

    goToSlide(slideIndex) {
        // Validate slideIndex
        if (slideIndex < 0 || slideIndex >= this.totalSlides) return;

        const currentSlideElement = document.querySelector('.slide.active');
        const targetSlideElement = document.querySelector(`[data-slide="${slideIndex}"]`);

        if (!targetSlideElement) return;

        // Remove active class from current slide
        if (currentSlideElement) {
            currentSlideElement.classList.remove('active');
        }

        // Add active class to target slide
        targetSlideElement.classList.add('active');

        this.currentSlide = slideIndex;
        this.updateSlideCounter();
        this.updateNavigationButtons();
        this.updateSlideSelector();

        // Add fade-in animation to slide content
        const slideContent = targetSlideElement.querySelector('.slide-content');
        if (slideContent) {
            slideContent.classList.add('fade-in');
            setTimeout(() => slideContent.classList.remove('fade-in'), 500);
        }
    }

    updateSlideCounter() {
        const currentSlideEl = document.getElementById('currentSlide');
        const totalSlidesEl = document.getElementById('totalSlides');
        
        if (currentSlideEl) currentSlideEl.textContent = this.currentSlide + 1;
        if (totalSlidesEl) totalSlidesEl.textContent = this.totalSlides;
    }

    updateNavigationButtons() {
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');

        if (prevBtn) {
            if (this.currentSlide === 0) {
                prevBtn.disabled = true;
                prevBtn.style.opacity = '0.5';
                prevBtn.style.cursor = 'not-allowed';
            } else {
                prevBtn.disabled = false;
                prevBtn.style.opacity = '1';
                prevBtn.style.cursor = 'pointer';
            }
        }

        if (nextBtn) {
            if (this.currentSlide === this.totalSlides - 1) {
                nextBtn.disabled = true;
                nextBtn.style.opacity = '0.5';
                nextBtn.style.cursor = 'not-allowed';
            } else {
                nextBtn.disabled = false;
                nextBtn.style.opacity = '1';
                nextBtn.style.cursor = 'pointer';
            }
        }
    }

    updateSlideSelector() {
        const slideSelector = document.getElementById('slideSelector');
        if (slideSelector) {
            slideSelector.value = this.currentSlide;
        }
    }

    initComponentInteractions() {
        const componentCards = document.querySelectorAll('.component-card');
        
        componentCards.forEach(card => {
            card.addEventListener('click', (e) => {
                e.preventDefault();
                const details = card.querySelector('.component-details');
                if (details) {
                    details.classList.toggle('hidden');
                    
                    // Add visual feedback
                    if (details.classList.contains('hidden')) {
                        card.style.background = '';
                    } else {
                        card.style.background = 'var(--color-secondary)';
                    }
                }
            });
        });
    }

    initPersonalityInteractions() {
        const personalityCards = document.querySelectorAll('.personality-card');
        
        personalityCards.forEach(card => {
            card.addEventListener('click', (e) => {
                e.preventDefault();
                const details = card.querySelector('.personality-details');
                if (details) {
                    details.classList.toggle('hidden');
                    
                    // Add visual feedback
                    if (details.classList.contains('hidden')) {
                        card.style.background = '';
                    } else {
                        card.style.background = 'var(--color-secondary)';
                    }
                }
            });
        });
    }

    initChartInteractions() {
        const chartContainers = document.querySelectorAll('.clickable-chart');
        
        chartContainers.forEach(chart => {
            chart.addEventListener('click', (e) => {
                e.preventDefault();
                const chartType = chart.dataset.chart;
                this.showChartDetails(chartType);
            });
        });
    }

    showChartDetails(chartType) {
        const modal = document.getElementById('chartModal');
        const modalContent = document.getElementById('modalContent');
        
        if (!modal || !modalContent) return;
        
        let content = '';
        
        switch(chartType) {
            case 'persuasiveness':
                content = this.getPersuasivenessDetails();
                break;
            case 'phases':
                content = this.getPhaseDetails();
                break;
            case 'comparison':
                content = this.getComparisonDetails();
                break;
        }
        
        modalContent.innerHTML = content;
        modal.classList.remove('hidden');
    }

    getPersuasivenessDetails() {
        return `
            <h2>Performance de Persuasion par Personnalité</h2>
            <div style="margin: 24px 0;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: var(--color-secondary);">
                            <th style="padding: 12px; text-align: left; border: 1px solid var(--color-border);">Personnalité</th>
                            <th style="padding: 12px; text-align: center; border: 1px solid var(--color-border);">Score de Persuasion</th>
                            <th style="padding: 12px; text-align: left; border: 1px solid var(--color-border);">Forces Principales</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="padding: 12px; border: 1px solid var(--color-border);"><strong>The Idealist</strong></td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border); color: var(--color-success);">85.1%</td>
                            <td style="padding: 12px; border: 1px solid var(--color-border);">Appel émotionnel, persuasion</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px; border: 1px solid var(--color-border);"><strong>The Populist</strong></td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border);">74.9%</td>
                            <td style="padding: 12px; border: 1px solid var(--color-border);">Lisibilité, appel émotionnel</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px; border: 1px solid var(--color-border);"><strong>The Scholar</strong></td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border);">74.0%</td>
                            <td style="padding: 12px; border: 1px solid var(--color-border);">Qualité des preuves, cohérence logique</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px; border: 1px solid var(--color-border);"><strong>The Philosopher</strong></td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border);">70.4%</td>
                            <td style="padding: 12px; border: 1px solid var(--color-border);">Nouveauté, cohérence logique</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px; border: 1px solid var(--color-border);"><strong>The Skeptic</strong></td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border);">69.5%</td>
                            <td style="padding: 12px; border: 1px solid var(--color-border);">Vérification des faits, cohérence logique</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px; border: 1px solid var(--color-border);"><strong>The Economist</strong></td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border);">68.2%</td>
                            <td style="padding: 12px; border: 1px solid var(--color-border);">Qualité des preuves, cohérence logique</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px; border: 1px solid var(--color-border);"><strong>The Pragmatist</strong></td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border); color: var(--color-warning);">64.5%</td>
                            <td style="padding: 12px; border: 1px solid var(--color-border);">Pertinence, lisibilité</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div style="background: var(--color-secondary); padding: 16px; border-radius: 8px; margin-top: 20px;">
                <h4>💡 Analyse clé</h4>
                <p>The Idealist domine grâce à son approche émotionnelle, tandis que The Pragmatist, malgré sa pertinence pratique, a le score le plus faible en raison d'un manque de nouveauté dans ses arguments.</p>
            </div>
        `;
    }

    getPhaseDetails() {
        return `
            <h2>Évolution de la Qualité par Phase de Débat</h2>
            <div style="margin: 24px 0;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: var(--color-secondary);">
                            <th style="padding: 12px; text-align: left; border: 1px solid var(--color-border);">Phase</th>
                            <th style="padding: 12px; text-align: center; border: 1px solid var(--color-border);">Score Moyen</th>
                            <th style="padding: 12px; text-align: left; border: 1px solid var(--color-border);">Caractéristiques</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="padding: 12px; border: 1px solid var(--color-border);"><strong>Opening</strong></td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border);">0.72</td>
                            <td style="padding: 12px; border: 1px solid var(--color-border);">Présentation des positions initiales</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px; border: 1px solid var(--color-border);"><strong>Main Arguments</strong></td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border);">0.76</td>
                            <td style="padding: 12px; border: 1px solid var(--color-border);">Développement des arguments principaux</td>
                        </tr>
                        <tr style="background: var(--color-success); color: var(--color-btn-primary-text);">
                            <td style="padding: 12px; border: 1px solid var(--color-border);"><strong>Rebuttals</strong></td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border);">0.81</td>
                            <td style="padding: 12px; border: 1px solid var(--color-border);">Phase de contre-argumentation (pic de qualité)</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px; border: 1px solid var(--color-border);"><strong>Closing</strong></td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border);">0.79</td>
                            <td style="padding: 12px; border: 1px solid var(--color-border);">Synthèse et arguments finaux</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div style="background: var(--color-secondary); padding: 16px; border-radius: 8px; margin-top: 20px;">
                <h4>📊 Insights</h4>
                <ul style="margin: 8px 0; padding-left: 20px;">
                    <li>La phase <strong>Rebuttals</strong> montre la qualité argumentative la plus élevée</li>
                    <li>Les agents s'améliorent progressivement jusqu'à la contre-argumentation</li>
                    <li>Légère baisse en <strong>Closing</strong> due à la synthèse moins détaillée</li>
                    <li>Progression générale de +12.5% entre Opening et Rebuttals</li>
                </ul>
            </div>
        `;
    }

    getComparisonDetails() {
        return `
            <h2>Comparaison Avant/Après Intégration GPT</h2>
            <div style="margin: 24px 0;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: var(--color-secondary);">
                            <th style="padding: 12px; text-align: left; border: 1px solid var(--color-border);">Métrique</th>
                            <th style="padding: 12px; text-align: center; border: 1px solid var(--color-border);">Base Locale</th>
                            <th style="padding: 12px; text-align: center; border: 1px solid var(--color-border);">Avec GPT</th>
                            <th style="padding: 12px; text-align: center; border: 1px solid var(--color-border);">Amélioration</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="padding: 12px; border: 1px solid var(--color-border);"><strong>Couverture des sujets</strong></td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border); color: var(--color-warning);">42%</td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border); color: var(--color-success);">89%</td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border); color: var(--color-success);"><strong>+112%</strong></td>
                        </tr>
                        <tr>
                            <td style="padding: 12px; border: 1px solid var(--color-border);"><strong>Qualité des arguments</strong></td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border);">58%</td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border); color: var(--color-success);">78%</td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border); color: var(--color-success);"><strong>+34%</strong></td>
                        </tr>
                        <tr>
                            <td style="padding: 12px; border: 1px solid var(--color-border);"><strong>Précision factuelle</strong></td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border);">61%</td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border); color: var(--color-success);">84%</td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border); color: var(--color-success);"><strong>+38%</strong></td>
                        </tr>
                        <tr>
                            <td style="padding: 12px; border: 1px solid var(--color-border);"><strong>Temps de réponse (s)</strong></td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border); color: var(--color-success);">3.2s</td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border); color: var(--color-warning);">4.1s</td>
                            <td style="padding: 12px; text-align: center; border: 1px solid var(--color-border); color: var(--color-warning);"><strong>+28%</strong></td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 20px;">
                <div style="background: var(--color-success); color: var(--color-btn-primary-text); padding: 16px; border-radius: 8px;">
                    <h4>✅ Bénéfices majeurs</h4>
                    <ul style="margin: 8px 0; padding-left: 20px;">
                        <li>Couverture élargie des sujets</li>
                        <li>Arguments plus nuancés</li>
                        <li>Meilleure précision factuelle</li>
                        <li>Adaptation aux domaines spécialisés</li>
                    </ul>
                </div>
                <div style="background: var(--color-warning); color: white; padding: 16px; border-radius: 8px;">
                    <h4>⚠️ Compromis acceptables</h4>
                    <ul style="margin: 8px 0; padding-left: 20px;">
                        <li>Temps de réponse légèrement plus long</li>
                        <li>Dépendance à une API externe</li>
                        <li>Coût additionnel par requête</li>
                    </ul>
                </div>
            </div>
        `;
    }

    closeModal() {
        const modal = document.getElementById('chartModal');
        if (modal) {
            modal.classList.add('hidden');
        }
    }
}

// Data for the application
const presentationData = {
    personalities: [
        {
            name: "The Scholar",
            description: "Académique et basé sur les preuves. S'appuie sur la recherche et les sources validées par les pairs.",
            strengths: ["evidence_quality", "logical_coherence"],
            weaknesses: ["emotional_appeal"],
            persuasiveness: 0.74
        },
        {
            name: "The Pragmatist", 
            description: "Se concentre sur les implications pratiques et les conséquences réelles.",
            strengths: ["relevance_score", "readability_score"],
            weaknesses: ["novelty_score"],
            persuasiveness: 0.645
        },
        {
            name: "The Idealist",
            description: "Argumente à partir de principes moraux et de fondements éthiques.",
            strengths: ["emotional_appeal", "persuasiveness"],
            weaknesses: ["evidence_quality"],
            persuasiveness: 0.851
        },
        {
            name: "The Skeptic",
            description: "Remet tout en question et exige des preuves rigoureuses.",
            strengths: ["fact_check_score", "logical_coherence"],
            weaknesses: ["emotional_appeal"],
            persuasiveness: 0.695
        },
        {
            name: "The Populist",
            description: "Représente le bon sens et l'opinion populaire. Parle un langage accessible.",
            strengths: ["readability_score", "emotional_appeal"],
            weaknesses: ["evidence_quality"],
            persuasiveness: 0.749
        },
        {
            name: "The Economist",
            description: "Analyse les problèmes à travers l'analyse coûts-bénéfices et les principes du marché.",
            strengths: ["evidence_quality", "logical_coherence"],
            weaknesses: ["emotional_appeal"],
            persuasiveness: 0.682
        },
        {
            name: "The Philosopher",
            description: "Explore des questions profondes sur le sens, l'éthique et les hypothèses fondamentales.",
            strengths: ["novelty_score", "logical_coherence"],
            weaknesses: ["readability_score"],
            persuasiveness: 0.704
        }
    ],
    debateTopics: [
        "Intelligence artificielle et emploi",
        "Énergie nucléaire vs renouvelables", 
        "Télétravail obligatoire",
        "Réseaux sociaux pour mineurs",
        "Voiture autonome"
    ],
    phases: ["Opening", "Main Arguments", "Rebuttals", "Closing"],
    phasePerformance: {
        "Opening": 0.72,
        "Main Arguments": 0.76,
        "Rebuttals": 0.81,
        "Closing": 0.79
    },
    comparison: {
        "Avec base de données locale": {
            coverage_topics: 0.42,
            argument_quality: 0.58,
            response_time: 3.2,
            factual_accuracy: 0.61
        },
        "Avec intégration GPT": {
            coverage_topics: 0.89,
            argument_quality: 0.78,
            response_time: 4.1,
            factual_accuracy: 0.84
        }
    }
};

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const app = new PresentationApp();
    
    // Add some visual enhancements
    setTimeout(() => {
        const titleSlide = document.querySelector('[data-slide="0"]');
        if (titleSlide && titleSlide.classList.contains('active')) {
            const slideContent = titleSlide.querySelector('.slide-content');
            if (slideContent) {
                slideContent.classList.add('fade-in');
            }
        }
    }, 100);
    
    console.log('Présentation IA Dialogique initialisée ✅');
    console.log('Navigation: Flèches ← → ou boutons/sélecteur');
    console.log('Interactions: Cliquez sur les composants et graphiques');
});