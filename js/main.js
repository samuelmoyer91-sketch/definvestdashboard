// Defense Capital Dashboard - Main JavaScript
// Chart rendering and interactive features

// Mobile menu toggle
document.addEventListener('DOMContentLoaded', function() {
    const menuToggle = document.querySelector('.mobile-menu-toggle');
    const navMenu = document.querySelector('nav ul');

    if (menuToggle) {
        menuToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
    }
});

// Chart configuration defaults
const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            display: true,
            position: 'top',
        },
        tooltip: {
            mode: 'index',
            intersect: false,
        }
    },
    scales: {
        x: {
            grid: {
                display: false
            }
        },
        y: {
            grid: {
                color: '#e0e0e0',
                drawBorder: false
            }
        }
    }
};

// Chart color scheme (teal theme)
const chartColors = {
    primary: '#226E93',
    primaryLight: '#2a87b3',
    accent: '#88c0d0',
    success: '#4caf50',
    warning: '#ff9800',
    error: '#f44336',
    gray: '#999999'
};

/**
 * Create a line chart from JSON data
 * @param {string} canvasId - ID of the canvas element
 * @param {object} data - Chart data object with dates and values
 * @param {object} options - Additional chart options
 */
function createLineChart(canvasId, data, options = {}) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error(`Canvas element ${canvasId} not found`);
        return null;
    }

    // Prepare chart data
    const chartData = {
        labels: data.data.map(d => d.date),
        datasets: [{
            label: data.name || data.series_id,
            data: data.data.map(d => d.value || d.close),
            borderColor: options.color || chartColors.primary,
            backgroundColor: options.fillColor || 'rgba(34, 110, 147, 0.1)',
            borderWidth: 2,
            fill: options.fill !== false,
            tension: 0.1,
            pointRadius: 0,
            pointHoverRadius: 4
        }]
    };

    // Merge options with defaults
    const chartOptions = {
        ...chartDefaults,
        ...options,
        plugins: {
            ...chartDefaults.plugins,
            ...(options.plugins || {}),
            title: {
                display: true,
                text: data.name || data.series_id,
                font: {
                    size: 16,
                    weight: 'bold'
                },
                color: '#1a5573'
            },
            subtitle: {
                display: !!data.description,
                text: data.description || '',
                font: {
                    size: 12
                },
                color: '#666666'
            }
        }
    };

    // Create chart
    return new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: chartOptions
    });
}

/**
 * Create a multi-line chart comparing multiple datasets
 * @param {string} canvasId - ID of the canvas element
 * @param {array} datasets - Array of data objects
 * @param {object} options - Additional chart options
 */
function createMultiLineChart(canvasId, datasets, options = {}) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error(`Canvas element ${canvasId} not found`);
        return null;
    }

    const colors = [
        chartColors.primary,
        chartColors.accent,
        chartColors.success,
        chartColors.warning
    ];

    // Prepare chart datasets
    const chartDatasets = datasets.map((dataset, index) => ({
        label: dataset.name || dataset.ticker || dataset.series_id,
        data: dataset.data.map(d => ({
            x: d.date,
            y: d.value || d.close
        })),
        borderColor: colors[index % colors.length],
        backgroundColor: 'transparent',
        borderWidth: 2,
        fill: false,
        tension: 0.1,
        pointRadius: 0,
        pointHoverRadius: 4
    }));

    const chartOptions = {
        ...chartDefaults,
        ...options,
        plugins: {
            ...chartDefaults.plugins,
            ...(options.plugins || {})
        }
    };

    return new Chart(ctx, {
        type: 'line',
        data: { datasets: chartDatasets },
        options: chartOptions
    });
}

/**
 * Load JSON data and create chart
 * @param {string} dataFile - Path to JSON data file
 * @param {string} canvasId - ID of canvas element
 * @param {object} options - Chart options
 */
async function loadAndRenderChart(dataFile, canvasId, options = {}) {
    try {
        const response = await fetch(dataFile);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return createLineChart(canvasId, data, options);
    } catch (error) {
        console.error(`Error loading chart data from ${dataFile}:`, error);
        const container = document.getElementById(canvasId)?.parentElement;
        if (container) {
            container.innerHTML = `<div class="error">Failed to load chart data: ${error.message}</div>`;
        }
        return null;
    }
}

/**
 * Load multiple datasets and create comparison chart
 * @param {array} dataFiles - Array of paths to JSON data files
 * @param {string} canvasId - ID of canvas element
 * @param {object} options - Chart options
 */
async function loadAndRenderMultiChart(dataFiles, canvasId, options = {}) {
    try {
        const responses = await Promise.all(dataFiles.map(file => fetch(file)));
        const datasets = await Promise.all(responses.map(r => r.json()));
        return createMultiLineChart(canvasId, datasets, options);
    } catch (error) {
        console.error('Error loading multi-chart data:', error);
        const container = document.getElementById(canvasId)?.parentElement;
        if (container) {
            container.innerHTML = `<div class="error">Failed to load chart data: ${error.message}</div>`;
        }
        return null;
    }
}

/**
 * Table sorting functionality
 * @param {HTMLTableElement} table - Table element to make sortable
 */
function makeSortable(table) {
    const headers = table.querySelectorAll('th');
    headers.forEach((header, index) => {
        header.style.cursor = 'pointer';
        header.addEventListener('click', () => {
            sortTable(table, index);
        });
    });
}

function sortTable(table, columnIndex) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const header = table.querySelectorAll('th')[columnIndex];
    const isAscending = header.classList.contains('sort-asc');

    // Remove sort indicators from all headers
    table.querySelectorAll('th').forEach(h => {
        h.classList.remove('sort-asc', 'sort-desc');
    });

    // Sort rows
    rows.sort((a, b) => {
        const aValue = a.cells[columnIndex].textContent.trim();
        const bValue = b.cells[columnIndex].textContent.trim();

        // Try to parse as numbers
        const aNum = parseFloat(aValue.replace(/[,$]/g, ''));
        const bNum = parseFloat(bValue.replace(/[,$]/g, ''));

        if (!isNaN(aNum) && !isNaN(bNum)) {
            return isAscending ? bNum - aNum : aNum - bNum;
        }

        // Compare as strings
        return isAscending
            ? bValue.localeCompare(aValue)
            : aValue.localeCompare(bValue);
    });

    // Update table
    rows.forEach(row => tbody.appendChild(row));

    // Update sort indicator
    header.classList.add(isAscending ? 'sort-desc' : 'sort-asc');
}

/**
 * Table search/filter functionality
 * @param {string} searchInputId - ID of search input
 * @param {string} tableId - ID of table to filter
 */
function setupTableSearch(searchInputId, tableId) {
    const searchInput = document.getElementById(searchInputId);
    const table = document.getElementById(tableId);

    if (!searchInput || !table) {
        console.error('Search input or table not found');
        return;
    }

    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const rows = table.querySelectorAll('tbody tr');

        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(searchTerm) ? '' : 'none';
        });
    });
}

/**
 * Update last updated timestamp
 * @param {string} elementId - ID of element to update
 * @param {string} timestamp - Timestamp string
 */
function updateTimestamp(elementId, timestamp) {
    const element = document.getElementById(elementId);
    if (element && timestamp) {
        const date = new Date(timestamp);
        element.textContent = `Last updated: ${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
    }
}

/**
 * Format number with commas
 * @param {number} num - Number to format
 * @returns {string} Formatted number
 */
function formatNumber(num) {
    return num.toLocaleString('en-US');
}

/**
 * Format currency
 * @param {number} num - Number to format
 * @returns {string} Formatted currency
 */
function formatCurrency(num) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(num);
}

/**
 * Calculate percentage change
 * @param {number} oldValue - Old value
 * @param {number} newValue - New value
 * @returns {string} Formatted percentage change
 */
function percentChange(oldValue, newValue) {
    const change = ((newValue - oldValue) / oldValue) * 100;
    const sign = change >= 0 ? '+' : '';
    return `${sign}${change.toFixed(2)}%`;
}

/**
 * Calculate data summary statistics
 * @param {array} data - Array of data points with date and value
 * @returns {object} Summary statistics
 */
function calculateStats(data) {
    if (!data || data.length === 0) return null;

    const sortedData = [...data].sort((a, b) => new Date(a.date) - new Date(b.date));
    const latest = sortedData[sortedData.length - 1];
    const latestValue = latest.value || latest.close;

    // Month change (last vs 1 month ago)
    const oneMonthAgo = sortedData.length > 1 ? sortedData[sortedData.length - 2] : null;
    const oneMonthValue = oneMonthAgo ? (oneMonthAgo.value || oneMonthAgo.close) : null;
    const monthChange = oneMonthValue ? latestValue - oneMonthValue : null;
    const monthChangePercent = oneMonthValue ? ((latestValue - oneMonthValue) / oneMonthValue) * 100 : null;

    // Year change (last vs ~12 months ago)
    const oneYearAgo = sortedData.length > 12 ? sortedData[sortedData.length - 13] : sortedData[0];
    const oneYearValue = oneYearAgo.value || oneYearAgo.close;
    const yearChange = latestValue - oneYearValue;
    const yearChangePercent = ((latestValue - oneYearValue) / oneYearValue) * 100;

    // Trend indicator
    let trend = '→'; // flat
    if (monthChangePercent !== null) {
        if (monthChangePercent > 1) trend = '↑';
        else if (monthChangePercent < -1) trend = '↓';
    }

    return {
        latest: latestValue,
        latestDate: latest.date,
        monthChange: monthChange,
        monthChangePercent: monthChangePercent,
        yearChange: yearChange,
        yearChangePercent: yearChangePercent,
        trend: trend
    };
}

/**
 * Download data as CSV
 * @param {object} data - Data object with name and data array
 * @param {string} filename - Output filename
 */
function downloadCSV(data, filename) {
    // Create CSV content
    let csv = 'Date,Value\n';
    data.data.forEach(row => {
        const value = row.value || row.close;
        csv += `${row.date},${value}\n`;
    });

    // Create blob and download
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || 'data.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

/**
 * Add recession shading to chart
 * @param {object} chartData - Chart.js data object
 * @param {array} recessions - Array of recession periods
 * @returns {object} Annotations configuration
 */
function addRecessionShading(chartData, recessions) {
    if (!recessions || recessions.length === 0) return {};

    const annotations = {};
    recessions.forEach((recession, index) => {
        annotations[`recession${index}`] = {
            type: 'box',
            xMin: recession.start,
            xMax: recession.end,
            backgroundColor: 'rgba(128, 128, 128, 0.1)',
            borderWidth: 0,
            label: {
                display: false
            }
        };
    });

    return {
        annotation: {
            annotations: annotations
        }
    };
}

// Load recession data globally
let recessionData = null;
fetch('data/recessions.json')
    .then(response => response.json())
    .then(data => {
        recessionData = data.recessions;
    })
    .catch(err => console.log('Recession data not available'));

// Export functions for use in other scripts
window.ChartUtils = {
    createLineChart,
    createMultiLineChart,
    loadAndRenderChart,
    loadAndRenderMultiChart,
    makeSortable,
    setupTableSearch,
    updateTimestamp,
    formatNumber,
    formatCurrency,
    percentChange,
    calculateStats,
    downloadCSV,
    addRecessionShading,
    chartColors
};
