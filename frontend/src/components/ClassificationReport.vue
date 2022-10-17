<template lang="pug">
v-card.table-wrapper
  v-toolbar(color="grey darken-3", dense, dark) 
    v-icon mdi-newspaper-variant
    .pl-2.pt-1 Classification Report
    v-spacer
    v-btn.mr-0(icon, small @click="$emit('close-dialog')")
      v-icon mdi-close
  v-card-text
    .pt-4
      h2 Confusion Matrix
      v-row.pb-2(no-gutters, justify="center", justify-sm="center", justify-md="center", justify-lg="center", justify-xl="center") 
        h2 predicted
        v-icon mdi-arrow-down-thick
        h2.pl-4 actual
        v-icon mdi-arrow-right-thick
      v-row(no-gutters, justify-md="center", justify-lg="center", justify-xl="center")
        v-col(cols="1", xs="2", sm="2", md="1", lg="1", xl="1")
        v-col(cols="1", v-for="(classifier, classIndex) in networkStats.idxToClass", :key="classIndex + 'classifier'") 
          h4 {{ classifier }}
      v-row(
        no-gutters,
        justify-md="center",
        justify-lg="center",
        justify-xl="center",
        v-for="(classifier, classIndex) in networkStats.idxToClass",
        :key="classIndex"
      )
        v-col.pr-1(cols="1", xs="2", sm="2", md="1", lg="1", xl="1") 
          h4 {{ classifier }}
        v-col(
          cols="1",
          v-for="(data, index) in networkStats.confusionMatrix[classIndex]",
          :key="`${classifier}_${classIndex}_${data}_${index}`"
        )
          | {{ data }}
    .pt-4
      h2.pb-2 Precision Recall
      v-row(no-gutters)
        v-col
          v-simple-table(dense)
            template(v-slot:default="")
              thead
                tr
                  th.text-leftClass
                  th.text-left Precision
                  th.text-left Recall
                  th.text-left Support
              tbody
                tr(v-for="item in precisionRecallTableData", :key="item.precision + item.recall")
                  td {{ item.className }}
                  td {{ item.precision.toFixed(3) }}
                  td {{ item.recall }}
                  td {{ item.support }}
        v-col
          precision-recall-curve-chart(v-if="!loading", :chart-data="datasets", :height="450", :dark="$vuetify.theme.dark", :key="$vuetify.theme.dark")
          v-container.fill-height(v-else)
            v-row(no-gutters, justify="center")
              v-progress-circular(color="amber darken-2", indeterminate="", size="150", width="14")
</template>

<script>
import PrecisionRecallCurveChart from "./PrecisionRecallCurveChart";

export default {
  mounted() {
    this.populatePrChartData();
  },
  components: {
    PrecisionRecallCurveChart,
  },
  computed: {
    precisionRecallTableData() {
      const data = [];
      for (let i = 0; i < this.networkStats.precisionScores.length; i++) {
        data.push({
          className: this.networkStats.idxToClass[i],
          precision: this.networkStats.precisionScores[i],
          recall: this.networkStats.recallScores[i],
          support: this.networkStats.support[i],
        });
      }
      return data;
    },
  },
  props: {
    networkStats: Object,
  },
  methods: {
    colorSelector(i) {
      switch (i) {
        case 0:
          return "#9575CD"; // deep-purple lighten-2
        case 1:
          return "#D4E157"; // lime lighten-1
        case 2:
          return "#FB8C00"; // orange darken-1
        case 3:
          return "#D32F2F"; // red darken-2
        case 4:
          return "#1976D2"; // blue darken-2
        case 5:
          return "#2E7D32"; // green darken-3
        case 6:
          return "#757575"; // grey darken-1
        case 7:
          return "#6D4C41"; // brown darken-1
        case 8:
          return "#1DE9B6"; // teal accent-3
        case 9:
          return "#7986CB"; // indigo lighten-2
        default:
          return "#FF8F00"; // amber darken-3
      }
    },
    populatePrChartData: async function () {
      this.loading = true;
      let datasets = [];
      for (let i = 0; i < this.networkStats.classPrecisionRecallCurves.length; i++) {
        let curveData = this.networkStats.classPrecisionRecallCurves[i];
        let precisionCurve = curveData.precision_curve;
        let recallCurve = curveData.recall_curve;
        let plotData = [];
        for (let j = 0; j < precisionCurve.length; j++) {
          plotData.push({
            y: precisionCurve[j],
            x: recallCurve[j],
          });
        }
        datasets.push({
          label: this.networkStats.idxToClass[i],
          fill: false,
          data: plotData,
          borderColor: this.colorSelector(i),
          showLine: true,
        });
      }
      this.datasets = { datasets: datasets };
      // chart.js does NOT want to cooperate AT ALL!!!!!!!!!!
      setTimeout(
        function () {
          this.loading = false;
        }.bind(this),
        750
      );
    },
  },
  data() {
    return {
      loading: true,
      datasets: {},
    };
  },
};
</script>

<style scoped>
.table-wrapper {
  min-width: 750px;
  overflow-x: auto;
}
</style>