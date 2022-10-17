<script>
import { Scatter, mixins } from "vue-chartjs";
const { reactiveProp } = mixins;

export default {
  extends: Scatter,
  mixins: [reactiveProp],
  props: {
    dark: Boolean,
    chartData: {
      type: Object,
      default: null,
    },
  },
  data() {
    return {
      options: {
        responsive: true,
        maintainAspectRatio: false,
        elements: {
          point: {
            radius: 2,
          },
        },
        scales: {
          yAxes: [
            {
              scaleLabel: {
                display: true,
                labelString: "Precision",
              },
              gridLines: {
                color: this.dark ? "rgba(255, 255, 255, 0.2)" : "rgba(0, 0, 0, 0.1)",
                //display: false,
              },
              display: true,
              ticks: {
                beginAtZero: true,
              },
            },
          ],
          xAxes: [
            {
              scaleLabel: {
                display: true,
                labelString: "Recall",
              },
              gridLines: {
                color: this.dark ? "rgba(255, 255, 255, 0.2)" : "rgba(0, 0, 0, 0.1)",
                //display: false,
              },
              display: true,
              ticks: {
                beginAtZero: true,
              },
            },
          ],
        },
      },
    };
  },
  mounted() {
    // this.chartData is created in the mixin.
    // If you want to pass options please create a local options object
    this.renderChart(this.chartData, this.options);
  },
};
</script>