/**
 * ===================================
 * PAYMENT PLAN ANALYSIS SYSTEM
 * Custom JavaScript Functions
 * ===================================
 */

// Global application state
window.PaymentPlanApp = {
    currentTheme: 'default',
    charts: {},
    tables: {},
    filters: {},
    settings: {
        animationEnabled: true,
        autoRefresh: false,
        refreshInterval: 30000
    }
};

/**
 * Initialize application when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Main application initialization
 */
function initializeApp() {
    console.log('🚀 Initializing Payment Plan Analysis System');
    
    // Initialize core components
    initializeTheme();
    initializeNavigation();
    initializeToasts();
    initializeLoadingStates();
    initializeChartDefaults();
    initializeTableEnhancements();
    initializeFormEnhancements();
    initializeAnimations();
    
    // Set up event listeners
    setupEventListeners();
    
    console.log('✅ Application initialized successfully');
}

/**
 * Theme Management
 */
function initializeTheme() {
    // Load saved theme preference
    const savedTheme = localStorage.getItem('paymentPlanTheme') || 'default';
    applyTheme(savedTheme);
}

function applyTheme(themeName) {
    document.body.className = document.body.className.replace(/theme-\w+/g, '');
    if (themeName !== 'default') {
        document.body.classList.add(`theme-${themeName}`);
    }
    window.PaymentPlanApp.currentTheme = themeName;
    localStorage.setItem('paymentPlanTheme', themeName);
}

function toggleDarkMode() {
    const isDark = document.body.classList.contains('dark-mode');
    document.body.classList.toggle('dark-mode', !isDark);
    localStorage.setItem('darkMode', !isDark);
}

/**
 * Navigation Enhancements
 */
function initializeNavigation() {
    // Set active navigation item
    setActiveNavigation();
    
    // Add smooth scrolling to anchor links
    addSmoothScrolling();
}

function setActiveNavigation() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(link => {
        link.classList.remove('active');
        const linkPath = new URL(link.href).pathname;
        if (linkPath === currentPath || (currentPath.includes(linkPath) && linkPath !== '/')) {
            link.classList.add('active');
        }
    });
}

function addSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

/**
 * Enhanced Toast Notifications
 */
function initializeToasts() {
    // Create toast container if it doesn't exist
    if (!document.getElementById('toast-container')) {
        createToastContainer();
    }
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '1080';
    document.body.appendChild(container);
    return container;
}

function showToast(message, type = 'success', options = {}) {
    const defaults = {
        duration: 5000,
        closable: true,
        icon: true,
        animation: true
    };
    
    const config = { ...defaults, ...options };
    const icons = {
        success: 'fas fa-check-circle',
        danger: 'fas fa-exclamation-triangle',
        warning: 'fas fa-exclamation-circle',
        info: 'fas fa-info-circle'
    };
    
    const toastId = 'toast-' + Date.now();
    const iconHtml = config.icon ? `<i class="${icons[type]} me-2"></i>` : '';
    
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white bg-${type}" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    ${iconHtml}${message}
                </div>
                ${config.closable ? '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>' : ''}
            </div>
        </div>
    `;
    
    const container = document.getElementById('toast-container') || createToastContainer();
    container.insertAdjacentHTML('beforeend', toastHtml);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        delay: config.duration,
        animation: config.animation
    });
    
    toast.show();
    
    // Enhanced animation
    if (config.animation) {
        toastElement.style.transform = 'translateX(100%)';
        toastElement.style.opacity = '0';
        
        requestAnimationFrame(() => {
            toastElement.style.transition = 'all 0.3s ease-out';
            toastElement.style.transform = 'translateX(0)';
            toastElement.style.opacity = '1';
        });
    }
    
    // Remove element after hide
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
    
    return toast;
}

/**
 * Loading States Management
 */
function initializeLoadingStates() {
    // Create global loading overlay
    createLoadingOverlay();
}

function createLoadingOverlay() {
    if (document.getElementById('global-loading')) return;
    
    const overlay = document.createElement('div');
    overlay.id = 'global-loading';
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
        <div class="loading-spinner"></div>
    `;
    document.body.appendChild(overlay);
}

function showLoading(message = 'Loading...') {
    const overlay = document.getElementById('global-loading');
    if (overlay) {
        overlay.classList.add('show');
    }
}

function hideLoading() {
    const overlay = document.getElementById('global-loading');
    if (overlay) {
        overlay.classList.remove('show');
    }
}

function setButtonLoading(button, isLoading, originalText = null) {
    if (isLoading) {
        if (!originalText) {
            originalText = button.innerHTML;
        }
        button.dataset.originalText = originalText;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
        button.disabled = true;
    } else {
        const savedText = button.dataset.originalText;
        if (savedText) {
            button.innerHTML = savedText;
            delete button.dataset.originalText;
        }
        button.disabled = false;
    }
}

/**
 * Chart.js Default Configuration
 */
function initializeChartDefaults() {
    if (typeof Chart !== 'undefined') {
        Chart.defaults.font.family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
        Chart.defaults.color = '#495057';
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.legend.labels.padding = 20;
        Chart.defaults.elements.arc.borderWidth = 2;
        Chart.defaults.elements.line.borderWidth = 3;
        Chart.defaults.elements.point.radius = 6;
        Chart.defaults.elements.point.hoverRadius = 8;
    }
}

function createChart(canvas, config) {
    const ctx = canvas.getContext('2d');
    const chartId = canvas.id || 'chart-' + Date.now();
    
    // Add responsive defaults
    const defaultConfig = {
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true
                    }
                }
            },
            elements: {
                arc: {
                    borderWidth: 2
                }
            }
        }
    };
    
    // Merge configurations
    const mergedConfig = mergeDeep(defaultConfig, config);
    
    const chart = new Chart(ctx, mergedConfig);
    window.PaymentPlanApp.charts[chartId] = chart;
    
    return chart;
}

/**
 * Table Enhancements
 */
function initializeTableEnhancements() {
    // Add sorting indicators
    addTableSortingIndicators();
    
    // Add row hover effects
    addTableHoverEffects();
    
    // Initialize table search
    initializeTableSearch();
}

function addTableSortingIndicators() {
    document.querySelectorAll('table[data-sortable] th').forEach(th => {
        if (th.dataset.sortable !== 'false') {
            th.style.cursor = 'pointer';
            th.innerHTML += ' <i class="fas fa-sort text-muted"></i>';
            
            th.addEventListener('click', function() {
                sortTable(this);
            });
        }
    });
}

function addTableHoverEffects() {
    document.querySelectorAll('.table tbody tr').forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.01)';
            this.style.transition = 'transform 0.2s ease';
        });
        
        row.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
}

function initializeTableSearch() {
    document.querySelectorAll('[data-table-search]').forEach(input => {
        const targetTable = document.querySelector(input.dataset.tableSearch);
        if (targetTable) {
            input.addEventListener('input', function() {
                filterTable(targetTable, this.value);
            });
        }
    });
}

function filterTable(table, searchTerm) {
    const rows = table.querySelectorAll('tbody tr');
    const term = searchTerm.toLowerCase();
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const isVisible = text.includes(term);
        row.style.display = isVisible ? '' : 'none';
        
        if (window.PaymentPlanApp.settings.animationEnabled) {
            row.style.opacity = isVisible ? '1' : '0';
            row.style.transform = isVisible ? 'translateX(0)' : 'translateX(-10px)';
        }
    });
}

/**
 * Form Enhancements
 */
function initializeFormEnhancements() {
    // Add floating labels effect
    addFloatingLabels();
    
    // Add form validation styling
    addFormValidation();
    
    // Add file upload enhancements
    enhanceFileUploads();
}

function addFloatingLabels() {
    document.querySelectorAll('.form-floating input, .form-floating select').forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            if (!this.value) {
                this.parentElement.classList.remove('focused');
            }
        });
    });
}

function addFormValidation() {
    document.querySelectorAll('form[data-validate]').forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    });
}

function enhanceFileUploads() {
    document.querySelectorAll('input[type="file"]').forEach(input => {
        input.addEventListener('change', function() {
            updateFileUploadDisplay(this);
        });
    });
}

/**
 * Animation System
 */
function initializeAnimations() {
    // Add entrance animations to elements
    addEntranceAnimations();
    
    // Add scroll animations
    addScrollAnimations();
}

function addEntranceAnimations() {
    if (!window.PaymentPlanApp.settings.animationEnabled) return;
    
    document.querySelectorAll('.card, .metric-card, .alert').forEach((element, index) => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            element.style.transition = 'all 0.5s ease';
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

function addScrollAnimations() {
    if (!window.PaymentPlanApp.settings.animationEnabled) return;
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, { threshold: 0.1 });
    
    document.querySelectorAll('[data-animate]').forEach(element => {
        observer.observe(element);
    });
}

/**
 * Event Listeners Setup
 */
function setupEventListeners() {
    // Window resize handler
    window.addEventListener('resize', debounce(handleWindowResize, 250));
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
    
    // Click outside modal handler
    document.addEventListener('click', handleOutsideClick);
    
    // Auto-refresh setup
    if (window.PaymentPlanApp.settings.autoRefresh) {
        setupAutoRefresh();
    }
}

function handleWindowResize() {
    // Redraw charts if they exist
    Object.values(window.PaymentPlanApp.charts).forEach(chart => {
        if (chart && typeof chart.resize === 'function') {
            chart.resize();
        }
    });
    
    // Adjust table responsiveness
    adjustTableResponsiveness();
}

function handleKeyboardShortcuts(e) {
    // Ctrl/Cmd + K for search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('[data-shortcut="search"]');
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    // Escape to close modals
    if (e.key === 'Escape') {
        const openModal = document.querySelector('.modal.show');
        if (openModal) {
            bootstrap.Modal.getInstance(openModal).hide();
        }
    }
}

/**
 * Utility Functions
 */
function formatCurrency(amount, options = {}) {
    const defaults = {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    };
    
    return new Intl.NumberFormat('en-US', { ...defaults, ...options }).format(amount);
}

function formatPercentage(value, decimals = 1) {
    return `${value.toFixed(decimals)}%`;
}

function formatDate(date, options = {}) {
    const defaults = {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    };
    
    return new Date(date).toLocaleDateString('en-US', { ...defaults, ...options });
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function mergeDeep(target, source) {
    const output = Object.assign({}, target);
    if (isObject(target) && isObject(source)) {
        Object.keys(source).forEach(key => {
            if (isObject(source[key])) {
                if (!(key in target))
                    Object.assign(output, { [key]: source[key] });
                else
                    output[key] = mergeDeep(target[key], source[key]);
            } else {
                Object.assign(output, { [key]: source[key] });
            }
        });
    }
    return output;
}

function isObject(item) {
    return item && typeof item === 'object' && !Array.isArray(item);
}

/**
 * API Helper Functions
 */
async function apiRequest(url, options = {}) {
    const defaults = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    const config = { ...defaults, ...options };
    
    try {
        showLoading();
        const response = await fetch(url, config);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('API request failed:', error);
        showToast(`Request failed: ${error.message}`, 'danger');
        throw error;
    } finally {
        hideLoading();
    }
}

async function downloadFile(url, filename) {
    try {
        showLoading();
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error('Download failed');
        }
        
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(downloadUrl);
        document.body.removeChild(a);
        
        showToast(`${filename} downloaded successfully`, 'success');
    } catch (error) {
        console.error('Download failed:', error);
        showToast('Download failed', 'danger');
    } finally {
        hideLoading();
    }
}

// Make functions globally available
window.showToast = showToast;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.formatCurrency = formatCurrency;
window.formatPercentage = formatPercentage;
window.formatDate = formatDate;
window.apiRequest = apiRequest;
window.downloadFile = downloadFile;

console.log('📦 Payment Plan Analysis System JavaScript loaded');