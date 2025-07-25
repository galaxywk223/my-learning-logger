document.addEventListener('DOMContentLoaded', function () {

    // --- 全局设置 ---
    Chart.register(ChartDataLabels);
    Chart.defaults.plugins.datalabels.display = false;
    lucide.createIcons();

    // --- DOM 元素和数据 ---
    const chartContainer = document.getElementById('chartsTabContent');
    if (!chartContainer) {
        console.error("Chart container #chartsTabContent not found!");
        return;
    }
    const URLS = {
        trends: chartContainer.dataset.trendsUrl,
        category: chartContainer.dataset.categoryUrl,
        wordcloud: chartContainer.dataset.wordcloudUrl
    };
    const MASK_OPTIONS = JSON.parse(chartContainer.dataset.maskOptions || '[]');
    const stageFilter = document.getElementById('stageFilter');

    // --- 标签页切换逻辑 ---
    const mainTabs = document.querySelectorAll('#chartsTab button[data-bs-toggle="tab"]');
    const trendsControls = document.getElementById('trends-controls');
    const filterControls = document.getElementById('filter-controls');

    mainTabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', event => {
            const targetId = event.target.id;
            const isTrendsTab = targetId === 'trends-tab';
            trendsControls.classList.toggle('d-none', !isTrendsTab);
            filterControls.classList.toggle('d-none', isTrendsTab);
        });
    });

    // --- 趋势分析模块 (保持不变) ---
    (function initTrendAnalysis() {
        let dataStore = {}, durationChart, efficiencyChart;
        const createChartOptions = t => ({
            responsive: true,
            maintainAspectRatio: false,
            interaction: {mode: 'index', intersect: false},
            layout: {padding: {bottom: 40}},
            plugins: {
                legend: {position: 'top', labels: {usePointStyle: true, boxWidth: 8, padding: 20}},
                tooltip: {
                    backgroundColor: '#1f2937',
                    titleFont: {size: 14},
                    bodyFont: {size: 12},
                    padding: 10,
                    cornerRadius: 6,
                    boxPadding: 3
                },
                stageAnnotations: {annotations: [], view: 'weekly'}
            },
            scales: {
                x: {grid: {display: false}, ticks: {display: false}},
                y: {title: {display: true, text: t}, grace: '5%', beginAtZero: true}
            }
        });
        const stageAnnotationsPlugin = {
            id: 'stageAnnotations', afterDraw: (chart) => {
                if (chart.config.options.plugins.stageAnnotations.view !== 'weekly') return;
                const {ctx, chartArea: {bottom, left, right}, scales: {x}} = chart;
                const annotations = chart.config.options.plugins.stageAnnotations.annotations;
                if (!annotations) return;
                ctx.save();
                ctx.font = 'bold 12px "Inter", sans-serif';
                ctx.textAlign = 'center';
                annotations.forEach(anno => {
                    const startIndex = chart.data.labels.indexOf(anno.start_week_label);
                    const endIndex = chart.data.labels.indexOf(anno.end_week_label);
                    if (startIndex === -1 || endIndex === -1) return;
                    const startPixel = x.getPixelForValue(startIndex);
                    const endPixel = x.getPixelForValue(endIndex);
                    const middlePixel = startPixel + (endPixel - startPixel) / 2;
                    if (middlePixel < left || middlePixel > right) return;
                    ctx.strokeStyle = '#9CA3AF';
                    ctx.lineWidth = 1;
                    ctx.fillStyle = '#4B5563';
                    ctx.beginPath();
                    ctx.moveTo(startPixel, bottom + 15);
                    ctx.lineTo(endPixel, bottom + 15);
                    ctx.stroke();
                    ctx.beginPath();
                    ctx.moveTo(middlePixel, bottom + 15);
                    ctx.lineTo(middlePixel, bottom + 20);
                    ctx.stroke();
                    ctx.fillText(anno.name, middlePixel, bottom + 35);
                });
                ctx.restore();
            }
        };
        const durationCtx = document.getElementById('durationChart')?.getContext('2d');
        const efficiencyCtx = document.getElementById('efficiencyChart')?.getContext('2d');

        if (!durationCtx || !efficiencyCtx) return;

        durationChart = new Chart(durationCtx, {
            type: 'bar',
            options: createChartOptions('学习时长 (小时)'),
            plugins: [stageAnnotationsPlugin]
        });
        efficiencyChart = new Chart(efficiencyCtx, {
            type: 'bar',
            options: createChartOptions('学习效率'),
            plugins: [stageAnnotationsPlugin]
        });

        async function fetchDataAndRender() {
            try {
                const response = await fetch(URLS.trends);
                if (!response.ok) throw new Error(`API request failed: ${response.statusText}`);
                const data = await response.json();
                if (!data.has_data) {
                    document.getElementById('trends-pane').innerHTML = '<div class="alert alert-info text-center">暂无学习数据，无法生成趋势图表。</div>';
                    return;
                }
                dataStore = data;
                document.getElementById('kpi-avg-time').textContent = data.kpis.avg_daily_formatted || 'N/A';
                document.getElementById('kpi-efficiency-star').textContent = data.kpis.efficiency_star || 'N/A';
                document.getElementById('kpi-weekly-trend').textContent = data.kpis.weekly_trend || 'N/A';
                updateCharts('weekly');
            } catch (error) {
                console.error('Error fetching trend data:', error);
                document.getElementById('trends-pane').innerHTML = `<div class="alert alert-danger">无法加载趋势图表数据，请稍后重试。</div>`;
            }
        }

        function updateCharts(view) {
            if (!dataStore.has_data || !dataStore[`${view}_duration_data`]) return;
            const durationData = dataStore[`${view}_duration_data`],
                efficiencyData = dataStore[`${view}_efficiency_data`];
            durationChart.data = {
                labels: durationData.labels,
                datasets: [{
                    type: 'bar',
                    label: '实际时长',
                    data: durationData.actuals,
                    backgroundColor: 'rgba(96, 165, 250, 0.5)',
                    order: 2
                }, {
                    type: 'line',
                    label: '趋势',
                    data: durationData.trends,
                    borderColor: '#2563EB',
                    tension: .4,
                    fill: false,
                    pointRadius: 0,
                    borderWidth: 2.5,
                    order: 1
                }]
            };
            efficiencyChart.data = {
                labels: efficiencyData.labels,
                datasets: [{
                    type: 'bar',
                    label: '实际效率',
                    data: efficiencyData.actuals,
                    backgroundColor: 'rgba(248, 113, 113, 0.5)',
                    order: 2
                }, {
                    type: 'line',
                    label: '趋势',
                    data: efficiencyData.trends,
                    borderColor: '#991B1B',
                    tension: .4,
                    fill: false,
                    pointRadius: 0,
                    borderWidth: 2.5,
                    order: 1,
                    spanGaps: true
                }]
            };
            durationChart.config.options.plugins.stageAnnotations = {
                annotations: dataStore.stage_annotations,
                view: view
            };
            efficiencyChart.config.options.plugins.stageAnnotations = {
                annotations: dataStore.stage_annotations,
                view: view
            };
            durationChart.update();
            efficiencyChart.update();
        }

        document.querySelectorAll('#trends-controls .btn').forEach(btn => btn.addEventListener('click', function () {
            document.querySelector('#trends-controls .btn.active').classList.remove('active');
            this.classList.add('active');
            updateCharts(this.dataset.view);
        }));
        fetchDataAndRender();
    })();

    // --- 分类分析模块 (保持不变) ---
    (function initCategoryAnalysis() {
        let doughnutChart, barChart, rawData, currentView = 'main', currentCategory = '';
        const doughnutCtx = document.getElementById('categoryDoughnutChart'),
            barCtx = document.getElementById('categoryBarChart');
        if (!doughnutCtx || !barCtx) return;
        const backButton = document.getElementById('backButton'),
            tableContainer = document.getElementById('category-table-container'),
            chartTitle = document.getElementById('categoryChartTitle'),
            doughnutCenterText = document.querySelector('#doughnut-center-text h3'),
            chartColors = ['#60A5FA', '#F87171', '#FBBF24', '#4ADE80', '#A78BFA', '#2DD4BF', '#F472B6', '#818CF8', '#FB923C', '#34D399'];
        const handleChartClick = (evt, elements, chart) => {
            if (elements.length > 0 && currentView === 'main') {
                const label = chart.data.labels[elements[0].index];
                if (rawData.drilldown[label] && rawData.drilldown[label].labels.length > 0) {
                    currentCategory = label;
                    currentView = 'drilldown';
                    updateAllCharts();
                }
            }
        };
        const handleChartHover = (evt, elements, chart) => {
            chart.canvas.style.cursor = elements.length > 0 && currentView === 'main' ? 'pointer' : 'default';
        };
        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            onHover: handleChartHover,
            onClick: handleChartClick
        };
        doughnutChart = new Chart(doughnutCtx, {
            type: 'doughnut',
            options: {
                ...commonOptions,
                cutout: '70%',
                plugins: {
                    legend: {display: false},
                    tooltip: {callbacks: {label: c => `${c.label || ''}: ${c.parsed.toFixed(1)}小时 (${(c.parsed / c.chart.getDatasetMeta(0).total * 100).toFixed(1)}%)`}},
                    datalabels: {
                        display: true, formatter: (value, context) => {
                            const dataset = context.chart.data.datasets[0];
                            if (!dataset || !dataset.data || dataset.data.length === 0) return null;
                            const total = dataset.data.reduce((t, datapoint) => t + datapoint, 0);
                            if (total === 0) return null;
                            const percentage = (value / total) * 100;
                            return percentage > 3 ? context.chart.data.labels[context.dataIndex] : null;
                        }, color: '#000000', backgroundColor: 'transparent', font: {weight: 'bold'}, padding: 4
                    }
                }
            }
        });
        barChart = new Chart(barCtx, {
            type: 'bar',
            options: {
                ...commonOptions,
                indexAxis: 'y',
                plugins: {
                    legend: {display: false},
                    tooltip: {enabled: true, callbacks: {label: c => `${c.label || ''}: ${c.parsed.toFixed(1)}小时`}}
                },
                scales: {x: {display: false, grid: {display: false}}, y: {grid: {display: false}}}
            }
        });

        async function fetchAndRenderAll() {
            try {
                const stageId = stageFilter.value;
                const response = await fetch(`${URLS.category}?stage_id=${stageId}`);
                if (!response.ok) throw new Error(`API request failed: ${response.statusText}`);
                rawData = await response.json();
                currentView = 'main';
                updateAllCharts();
            } catch (error) {
                console.error('Error fetching category data:', error);
                document.getElementById('category-pane').innerHTML = `<div class="alert alert-danger">无法加载分类图表数据。</div>`;
            }
        }

        function updateAllCharts() {
            let dataForDoughnut, dataForBar, dataForTable, title;
            const TOP_N = 10;
            if (currentView === 'drilldown') {
                title = `${currentCategory} - 标签详情`;
                backButton.style.display = 'inline-block';
                const sortedDrilldown = rawData.drilldown[currentCategory].labels.map((l, i) => ({
                    label: l,
                    value: rawData.drilldown[currentCategory].data[i]
                })).sort((a, b) => b.value - a.value);
                dataForDoughnut = sortedDrilldown;
                dataForBar = sortedDrilldown.slice(0, TOP_N);
                dataForTable = sortedDrilldown;
            } else {
                title = '分类时长占比';
                backButton.style.display = 'none';
                const sortedMain = rawData.main.labels.map((l, i) => ({
                    label: l,
                    value: rawData.main.data[i]
                })).sort((a, b) => b.value - a.value);
                dataForDoughnut = sortedMain;
                dataForBar = sortedMain.slice(0, TOP_N);
                dataForTable = sortedMain;
            }
            chartTitle.textContent = title;
            if (dataForTable && dataForTable.length > 0) {
                const totalHours = dataForTable.reduce((sum, item) => sum + item.value, 0);
                doughnutChart.data = {
                    labels: dataForDoughnut.map(d => d.label),
                    datasets: [{
                        data: dataForDoughnut.map(d => d.value),
                        backgroundColor: chartColors,
                        borderWidth: 2,
                        borderColor: 'transparent'
                    }]
                };
                barChart.data = {
                    labels: dataForBar.map(d => d.label),
                    datasets: [{
                        data: dataForBar.map(d => d.value),
                        backgroundColor: chartColors,
                        borderWidth: 2,
                        borderColor: 'transparent'
                    }]
                };
                doughnutChart.update();
                barChart.update();
                doughnutCenterText.textContent = `${totalHours.toFixed(1)}h`;
                renderTable(dataForTable, totalHours);
            } else {
                document.getElementById('category-pane').innerHTML = `<div class="alert alert-info text-center">当前筛选范围内没有找到任何带分类的学习记录。</div>`;
            }
        }

        function renderTable(data, total) {
            let tableHtml = '<table class="table table-hover"><thead><tr><th>名称</th><th>时长(h)</th><th>占比(%)</th></tr></thead><tbody>';
            data.forEach((item) => {
                const percentage = total > 0 ? (item.value / total * 100).toFixed(1) : 0;
                const drilldownAttr = (currentView === 'main' && rawData.drilldown[item.label] && rawData.drilldown[item.label].labels.length > 0) ? `data-drilldown-target="${item.label}" style="cursor: pointer;"` : '';
                tableHtml += `<tr ${drilldownAttr}><td>${item.label}</td><td>${item.value.toFixed(1)}</td><td>${percentage}%</td></tr>`;
            });
            tableHtml += '</tbody></table>';
            tableContainer.innerHTML = tableHtml;
            tableContainer.querySelectorAll('tr[data-drilldown-target]').forEach(row => {
                row.addEventListener('click', () => {
                    currentCategory = row.dataset.drilldownTarget;
                    currentView = 'drilldown';
                    updateAllCharts();
                });
            });
        }

        stageFilter.addEventListener('change', fetchAndRenderAll);
        backButton.addEventListener('click', () => {
            currentView = 'main';
            updateAllCharts();
        });
        let isCategoryTabLoaded = false;
        document.getElementById('category-tab').addEventListener('shown.bs.tab', () => {
            if (!isCategoryTabLoaded) {
                fetchAndRenderAll();
                isCategoryTabLoaded = true;
            }
        });
    })();

    // --- 词云分析模块 (最终修正版) ---
    (function initWordcloudAnalysis() {
        const wordcloudTab = document.getElementById('wordcloud-tab');
        const paletteSelector = document.getElementById('paletteSelector');
        const maskContainer = document.getElementById('mask-selector-container');
        const wordcloudContainer = document.getElementById('wordcloud-container');

        let isWordcloudLoaded = false;
        let currentMask = 'random';
        let currentImageObjectUrl = null;

        // *** 新增：UI状态管理函数 ***
        function showLoadingState() {
            wordcloudContainer.innerHTML = `
                <div class="d-flex flex-column align-items-center">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-2 text-muted">正在生成词云，请稍候...</p>
                </div>`;
        }

        function showImageState(imageUrl) {
            wordcloudContainer.innerHTML = `<img src="${imageUrl}" alt="笔记词云" style="max-width: 100%; max-height: 500px; height: auto; opacity: 0; transition: opacity 0.5s;" onload="this.style.opacity='1'">`;
        }

        function showNoDataState(message) {
            wordcloudContainer.innerHTML = `<div class="alert alert-light text-center">${message}</div>`;
        }

        // 动态创建蒙版选择器
        function createMaskSelector() {
            if (!maskContainer) return;
            maskContainer.innerHTML = '';

            MASK_OPTIONS.forEach(opt => {
                let maskElement;
                if (opt.file === 'random') {
                    maskElement = document.createElement('div');
                    maskElement.innerHTML = `<i data-lucide="shuffle" style="width: 20px; height: 20px;"></i>`;
                } else {
                    maskElement = document.createElement('img');
                    maskElement.src = `/static/images/masks/${opt.file}`;
                }

                maskElement.title = opt.name;
                maskElement.classList.add('mask-option');
                maskElement.dataset.mask = opt.file;

                if (opt.file === currentMask) {
                    maskElement.classList.add('active');
                }

                maskElement.addEventListener('click', function() {
                    maskContainer.querySelector('.mask-option.active')?.classList.remove('active');
                    this.classList.add('active');
                    currentMask = this.dataset.mask;
                    loadWordCloud();
                });
                maskContainer.appendChild(maskElement);
            });
            lucide.createIcons();
        }

        // 核心加载函数
        function loadWordCloud() {
            const stageId = stageFilter.value;
            const selectedPalette = paletteSelector.value;
            const timestamp = new Date().getTime();

            const apiUrl = `${URLS.wordcloud}?stage_id=${stageId}&mask=${currentMask}&palette=${selectedPalette}&t=${timestamp}`;

            showLoadingState();

            fetch(apiUrl)
                .then(response => {
                    if (response.status === 204) {
                        showNoDataState('在当前筛选的范围内没有找到任何笔记内容来生成词云。');
                        return null;
                    }
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.blob();
                })
                .then(blob => {
                    if (blob) {
                        if (currentImageObjectUrl) {
                            URL.revokeObjectURL(currentImageObjectUrl);
                        }
                        currentImageObjectUrl = URL.createObjectURL(blob);
                        showImageState(currentImageObjectUrl);
                    }
                })
                .catch(error => {
                    console.error('Error loading word cloud:', error);
                    showNoDataState('加载词云时发生网络错误，请稍后重试。');
                });
        }

        // 初始化
        createMaskSelector();

        // 事件监听
        wordcloudTab.addEventListener('shown.bs.tab', () => {
            if (!isWordcloudLoaded) {
                loadWordCloud();
                isWordcloudLoaded = true;
            }
        });

        paletteSelector.addEventListener('change', loadWordCloud);

        stageFilter.addEventListener('change', () => {
            if (wordcloudTab.classList.contains('active')) {
                loadWordCloud();
            } else {
                isWordcloudLoaded = false;
            }
        });
    })();
});
