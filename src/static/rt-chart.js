$(document).ready(function () {
    const config = {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: "",
                borderWidth: 4,
                backgroundColor: 'rgb(99, 120, 302)',
                borderColor: 'rgb(255, 99, 132)',
                borderColor: [],
                data: [],
                backgroundColor: []
            }],
        },
        options: {
            responsive: true,
            title: {
                display: true,
                text: 'CognitiveFX: Interactive Response Time Chart'
            },
            tooltips: {
                mode: 'index',
                intersect: false,
            },
            hover: {
                mode: 'nearest',
                intersect: true
            },
            scales: {
                xAxes: [{
                    display: true,
                    scaleLabel: {
                        display: true,
                        labelString: 'Timeline'
                    }
                }],
                yAxes: [{
                    display: true,
                    type: 'linear',
                    scaleLabel: {
                        display: true,
                        labelString: 'Response Delay (ms)'
                    }
                }]
            }
        }
    };

    var chartBorderColors = {
        red: 'rgb(255, 99, 132)',
        blue: 'rgb(0, 0, 235)',
        green: 'rgb(0, 128, 0)',
        yellow: 'rgb(255, 255, 0)'
    };

    var chartBackgroundColors = {
        red: 'rgb(255, 204, 204)',
        blue: 'rgb(204, 255, 235)',
        green: 'rgb(204, 255, 204)',
        yellow: 'rgb(255, 255, 204)'
    };

    var chartBackgroundColorsArray = [
        'rgb(204, 255, 255)',
        'rgb(229, 229, 229)',
        'rgb(255, 229, 204)'
    ];

    const context = document.getElementById('canvas').getContext('2d');

    const lineChart = new Chart(context, config);

    const source = new EventSource("/chart-data");

    source.onmessage = function (event) {
        const data = JSON.parse(event.data);
        if (config.data.labels.length === 20) {
            config.data.labels.shift();
            config.data.datasets[0].data.shift();
            config.data.datasets[0].backgroundColor.shift();
            config.data.datasets[0].borderColor.shift();
        }
        config.data.labels.push(data.time);
        config.data.datasets[0].data.push(data.value);
        config.data.datasets[0].backgroundColor.push (chartBackgroundColorsArray[data.device]);


        if (Math.abs(data.value) > 500) {
            config.data.datasets[0].borderColor.push (chartBorderColors.red);
        } else if (Math.abs(data.value) > 100) {
            config.data.datasets[0].borderColor.push (chartBorderColors.yellow);
        } else {
            config.data.datasets[0].borderColor.push (chartBorderColors.green);
        }
        
        lineChart.update();
    }
});