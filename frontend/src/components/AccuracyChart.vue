<script>
import { Line, mixins } from "vue-chartjs";
const { reactiveProp } = mixins;

export default {
  extends: Line,
  mixins: [reactiveProp],
  props: {
    dark: Boolean
  },
  data() {
    return {
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          yAxes: [
            {
              display: true,
              gridLines: {
                color: this.dark ? "rgba(255, 255, 255, 0.2)" : "rgba(0, 0, 0, 0.1)",
                //display: false,
              },
              labelString: "%",
              ticks: {
                beginAtZero: true,
                stepSize: 20,
                min: 0,
                max: 100,
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