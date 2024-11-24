<template>
  <div class="mainContainer">
    <div class="buttonContainer">
      <SplitButton :label="updateTypes[0].label" @click="updateTypes[0].command" :model="updateTypes.slice(1)" />
      <Button label="Expand all" @click="expandAll" />
      <Button label="Collapse all" @click="collapseAll" />
    </div>
    <Panel>
      <TreeTable
        v-model:expandedKeys="expandedKeys"
        :resizable-columns="false"
        :value="tree"
        class="mt-6"
        table-style="min-width: 10rem"
      >
        <Column sort-field="date" sortable expander style="width: 13rem">
          <template #body="{ node }">
            <a :href="node.data.page_link">{{ node.key }}</a>
          </template>
        </Column>
        <Column
          field="amount"
          header="Amount"
          class="dim right"
          style="width: 5rem"
        ></Column>
        <Column header="Cost (¥)" class="dim price right">
          <template #body="{ node }">
            {{ node.data.price.toLocaleString() + ' ¥' }}
          </template>
        </Column>
        <Column header="Cost ($)" class="dim price right">
          <template #body="{ node }">
            {{ (node.data.price * yenToUsd).toLocaleString() + ' $' }}
          </template>
        </Column>
        <Column header="In stock" class="dim right" style="width: 6rem">
          <template #body="{ node }">
            <span
              :class="{
                'in-stock': node.data.in_stock_flag,
                'out-of-stock': !node.data.in_stock_flag,
              }"
            >
              {{ node.data.in_stock_flag ? '✔️' : '❌' }}
            </span>
          </template>
        </Column>
        <Column header="Name" field="name" style="width: auto"> </Column>
      </TreeTable>
    </Panel>
    <Panel class="analytics">
      <template #header>
        <h3>Analytics</h3>
      </template>
      <Panel header="basic stats" toggleable class="basicAnalitics">
        <DataTable
          id="byTypeDataTable"
          :value="Object.entries(figureTypesCount)"
          size="small"
          style="text-align: right"
          :row-style="totalRowStyle"
        >
          <Column field="0" header="Type"></Column>
          <Column header="Count" class="right">
            <template #body="{ data }">
              {{ data[1].count.toLocaleString() }}
            </template>
          </Column>
          <Column header="Cost (¥)" class="right">
            <template #body="{ data }">
              {{ data[1].cost.toLocaleString() }}¥
            </template>
          </Column>
          <Column header="Cost ($)" class="right">
            <template #body="{ data }">
              {{ (data[1].cost * yenToUsd).toLocaleString() }}$
            </template>
          </Column>
        </DataTable>
      </Panel>
      <Divider />
      <Panel header="charts">
        <div class="chart-container">
          <canvas id="costPerMonthChart"></canvas>
        </div>
      </Panel>
    </Panel>
  </div>
  <div v-if="loading" class="overlay">
    <ProgressSpinner />
  </div>
  <Toast position="center" severity="danger" />
</template>

<script setup>
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Divider from 'primevue/divider'
import Panel from 'primevue/panel'
import ProgressSpinner from 'primevue/progressspinner'
import SplitButton from 'primevue/splitbutton';
import Toast from 'primevue/toast'
import TreeTable from 'primevue/treetable'
import { useToast } from 'primevue/usetoast'
import { computed, onMounted, ref } from 'vue'
const toast = useToast()

import Chart from 'chart.js/auto'
Chart.defaults.color = '#fff'

import axios from 'axios'

const yenToUsd = 0.0065

const loading = ref(false)

const tree = ref([])
const expandedKeys = ref()

const updateTypes = [
  { 
    label: 'Update current orders',
    command:  (event) => triggerDataUpdate(event, 'current_month')
  },
  { 
    label: 'Update all orders',
    command:  (event) => triggerDataUpdate(event, 'all')
  },
  { 
    label: 'Update open orders',
    command:  (event) => triggerDataUpdate(event, 'open')
  },
]

// expansion control

const initExpandedKeys = (nodes, levelValue = true) => {
  const keys = {}
  nodes.forEach((node) => {
    keys[node.key] = levelValue
    if (node.children) {
      Object.assign(keys, initExpandedKeys(node.children, false))
    }
  })
  return keys
}

const changeExpansion = (nodes, value) => {
  const changeExpansionRecursiveFuncion = (nodes) => {
    const keys = {}
    nodes.forEach((node) => {
      keys[node.key] = value
      if (node.children) {
        Object.assign(keys, changeExpansionRecursiveFuncion(node.children))
      }
    })
    return keys
  }

  expandedKeys.value = changeExpansionRecursiveFuncion(tree.value)
}

const expandAll = () => {
  changeExpansion(tree.value, true)
}

const collapseAll = () => {
  changeExpansion(tree.value, false)
}

// stats

const figureTypesCount = computed(() => {
  var typesCount = {}
  tree.value.forEach((month) => {
    month.children.forEach((order) => {
      order.children.forEach((item) => {
        var type
        const scaleMatch = item.data.name.match(/1\/\d{1,2}/)
        if (scaleMatch) {
          type = `${scaleMatch[0]} scale`
        } else if (item.data.name.includes('Nendoroid')) {
          type = 'nendoroid'
        } else if (item.data.scode.includes('GOODS')) {
          type = 'goods'
        } else {
          type = 'other'
        }
        if (!typesCount[type]) {
          typesCount[type] = { count: 0, cost: 0 }
        }
        typesCount[type].count++
        typesCount[type].cost += item.data.price
      })
    })
  })

  typesCount = Object.keys(typesCount)
    .sort()
    .reduce((acc, key) => {
      acc[key] = typesCount[key]
      return acc
    }, {})
  typesCount['TOTAL'] = {
    count: tree.value.reduce((acc, order) => acc + order.children.length, 0),
    cost: tree.value.reduce((acc, order) => acc + order.data.price, 0),
  }

  return typesCount
})

const totalRowStyle = (data) => {
  if (data[0] === 'TOTAL') {
    return {
      'font-weight': 'bold',
    }
  }
}

// chart

const costPerMonth = computed(() => {
  const costByMonth = {}
  const allMonths = new Set()
  const startDate = new Date(
    Math.min(...tree.value.map((order) => new Date(order.data.date)))
  )
  const endDate = new Date(
    Math.max(...tree.value.map((order) => new Date(order.data.date)))
  )

  for (let d = startDate; d <= endDate; d.setMonth(d.getMonth() + 1)) {
    const month = d.toISOString().slice(0, 7)
    allMonths.add(month)
  }

  allMonths.forEach((month) => {
    costByMonth[month] = 0
  })
  tree.value.forEach((month) => {
    month.children.forEach((order) => {
      const monthKey = order.data.date.slice(0, 7)
      costByMonth[monthKey] += order.data.price
    })
  })
  return Object.keys(costByMonth)
    .sort()
    .reduce((acc, key) => {
      acc[key] = costByMonth[key]
      return acc
    }, {})
})

let chartInstance = null;

const createChart = (ctx, data) => {
  if (chartInstance) {
    chartInstance.destroy();
  }
  chartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: Object.keys(data),
      datasets: [
        {
          label: 'cost per month',
          data: Object.values(data),
          backgroundColor: '#34d399',
          borderWidth: 0,
          yAxisID: 'y',
        },
      ],
    },
    options: {
      scales: {
        y: {
          beginAtZero: true,
          position: 'left',
          title: {
            display: true,
            text: 'Cost (¥)',
          },
        },
        y1: {
          beginAtZero: true,
          position: 'right',
          title: {
            display: true,
            text: 'Cost ($)',
          },
          grid: {
            drawOnChartArea: false,
          },
          ticks: {
            callback: function (value) {
              return (
                value *
                yenToUsd *
                this.chart.scales.y.max
              ).toLocaleString()
            },
          },
        },
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: function (context) {
              const yenValue = context.raw
              const usdValue = (yenValue * yenToUsd).toLocaleString()
              return `${yenValue.toLocaleString()}¥ / ${usdValue}$`
            },
          },
        },
      },
    },
  })
}

// basic data retrival and transformation

const getOrdersData = async () => {
  try {
    const response = await axios({
      method: 'get',
      url: '/api/orders/',
    })
    return response.data
  } catch (e) {
    console.error(e)
    toast.add({
      severity: 'danger',
      summary: 'Error',
      detail: `Failed to fetch data: ${e}`,
    })
    return []
  }
}

const postUpdateDataRequest = async (orderType) => {
  try {
    const response = await axios({
      method: 'post',
      url: '/api/orders/update/',
      params: {
        order_type: orderType,
      },
    })
    return response.data
  } catch (e) {
    console.error(e)
    toast.add({
      severity: 'danger',
      summary: 'Error',
      detail: `Failed to update data: ${e}`,
    })
    return []
  }
}

const triggerDataUpdate = async (event, orderType = 'current_month') => {
  loading.value = true
  try {
    await postUpdateDataRequest(orderType)
    tree.value = ordersDataToTree(await getOrdersData())
    expandedKeys.value = initExpandedKeys(tree.value)
    createChart(
      document.getElementById('costPerMonthChart').getContext('2d'),
      costPerMonth.value
    )
  } finally {
    loading.value = false
  }
}

const ordersDataToTree = (ordersData) => {
  const orders_as_tree = ordersData.map((order) => {
    const order_node = {
      key: order.id,
      data: order,
      children: order.items.map((item) => {
        const item_note = {
          key: item.id,
          data: item,
        }
        item_note.amount = item.amount
        return item_note
      }),
    }
    order_node.data.amount = order_node.children.reduce(
      (acc, item) => acc + item.data.amount,
      0
    )
    order_node.data.in_stock_flag = order_node.children.every(
      (item) => item.data.in_stock_flag
    )
    return order_node
  })

  const by_release_dates = {}

  for (const order of orders_as_tree) {
    const date = order.data.date
    by_release_dates[date] = by_release_dates[date] || []
    by_release_dates[date].push(order)
  }

  const treeData = Object.keys(by_release_dates).map((date) => {
    const month_node = {
      key: date.substring(0, 7),
      data: {
        date: date,
      },
      children: by_release_dates[date],
    }
    month_node.data.price = by_release_dates[date].reduce(
      (acc, order) => acc + order.data.price,
      0
    )
    month_node.data.amount = month_node.children.reduce(
      (acc, order) => acc + order.data.amount,
      0
    )
    month_node.data.in_stock_flag = month_node.children.every(
      (order) => order.data.in_stock_flag
    )
    return month_node
  })
  return treeData.sort((a, b) => (a.key < b.key ? -1 : 1))
}

// hooks

onMounted(async () => {
  tree.value = ordersDataToTree(await getOrdersData())
  expandedKeys.value = initExpandedKeys(tree.value)
  createChart(
    document.getElementById('costPerMonthChart').getContext('2d'),
    costPerMonth.value
  )
})
</script>

<style>
body {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
}

.overlay {
  position: fixed;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: center;
}

a {
  color: whitesmoke;
}

.p-treetable-tbody > tr[aria-level='2'] {
  background-color: black;
  color: white;
}
.p-treetable-tbody > tr[aria-level='3'] {
  background-color: black;
  color: white;
}

.p-treetable-tbody > tr[aria-level='1'] > td.dim {
  color: grey;
}

.p-treetable-tbody > tr[aria-level='3'] > td.dim {
  color: grey;
}

.p-treetable-tbody > tr > td.right > div,
.p-treetable-thead > tr > th.right > div {
  justify-content: right;
}

.p-datatable-tbody > tr > td.right,
.p-datatable-thead > tr > th.right > div {
  text-align: right;
  justify-content: right;
}
.p-treetable-tbody > tr > td.price {
  width: 8rem;
}

span.in-stock {
  color: transparent;
  text-shadow: 0 0 0 green;
}
.analytics {
  margin-top: 1rem;
  text-align: left;
}
.chart-container {
  width: 40%;
  color: white;
}
.buttonContainer {
  display: flex;
  justify-content: center;
  margin-top: 20px;
  gap: 20px;
}
.mainContainer {
  display: flex;
  flex-flow: column;
  gap: 1rem;
}

#byTypeDataTable {
  width: 40%;
}
.p-toast {
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  border-radius: 10px;
}
</style>
