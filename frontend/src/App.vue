<template>
  <div class="mainContainer">
    <div class="buttonContainer">
      <SplitButton :label="defaultUpdateType.label"  @click="defaultUpdateType.command" :model="updateTypes" />
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
        <Column expander style="width: 13rem">
          <template #body="{ node }">
            <a target="_blank" rel="noopener noreferrer" :href="node.data.page_link">{{ node.key }}</a>
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
            {{ Math.round(node.data.price * yenToUsd).toLocaleString() + ' $' }}
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
      <div class="dataSelectorContainer">
        <FloatLabel>
          <DatePicker v-model="analiticsStartDate" view="month" dateFormat="mm/yy" :minDate="dataStartDate" :maxDate="dataEndDate"/>
          <label for="over_label">Start date</label>
        </FloatLabel>
        <FloatLabel>
          <DatePicker v-model="analiticsEndDate" view="month" dateFormat="mm/yy" :minDate="dataStartDate" :maxDate="dataEndDate"/>
          <label for="over_label">End date</label>
        </FloatLabel>
      </div>
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
              {{ Math.round(data[1].cost * yenToUsd).toLocaleString() }}$
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

<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Divider from 'primevue/divider'
import FloatLabel from 'primevue/floatlabel'
import Panel from 'primevue/panel'
import ProgressSpinner from 'primevue/progressspinner'
import SplitButton from 'primevue/splitbutton'
import Toast from 'primevue/toast'
import TreeTable from 'primevue/treetable'
import { useToast } from 'primevue/usetoast'
import { computed, onMounted, ref, watch } from 'vue'
const toast = useToast()

import Chart from 'chart.js/auto'
Chart.defaults.color = '#fff'

import axios from 'axios'
import { MenuItem, MenuItemCommandEvent } from 'primevue/menuitem'

const yenToUsd = 0.0065

const loading = ref(false)

const now = new Date()
const current_month = new Date(now.getFullYear(), now.getMonth(), 1)

interface Item {
  id: string
  name: string
  price: number
  amount: number
  scode: string
  in_stock_flag: boolean
}

interface Order {
  id: string
  date: string
  price: number
  amount: number
  items: Item[]
  in_stock_flag: boolean
}

interface StatusNode {
  key: string
  data: {
    date: string
    price: number
    amount: number
    in_stock_flag: boolean
  }
  children: MonthNode[]
}

interface MonthNode {
  key: string
  data: {
    date: string
    price: number
    amount: number
    in_stock_flag: boolean
  }
  children: OrderNode[]
}

interface OrderNode {
  key: string
  data: Order
  children: ItemNode[]
}

interface ItemNode {
  key: string
  data: Item
}

interface TreeNode {
  key: string
  data: {
    date: string
    price: number
    amount: number
    in_stock_flag: boolean
  }
  children: TreeNode[]
}

interface Data {
  by_month: Record<string, Order[]>
  by_status: Record<string, Order[]>
  orders: Order[]
  startDate: Date
  endDate: Date
  oldestActiveOrderDate: Date
}

var ordersData: Order[] = []
var data: Data = {
  by_month: {},
  by_status: {},
  orders: [],
  startDate: new Date(),
  endDate: new Date(),
  oldestActiveOrderDate: new Date(),
}
const tree = ref<StatusNode[]>([])
const expandedKeys = ref<Record<string, boolean>>()

const dataStartDate = ref<Date>(new Date())
const dataEndDate = ref<Date>(new Date())

const analiticsStartDate = ref<Date | null>(null)
const analiticsEndDate = ref<Date | null>(null)

const updateTypes: MenuItem[] = [
  {
    label: 'Update current orders',
    command:  (event: MenuItemCommandEvent) => triggerDataUpdate(event, 'current_month')
  },
  {
    label: 'Update all orders',
    command:  (event: MenuItemCommandEvent) => triggerDataUpdate(event, 'all')
  },
  {
    label: 'Update open orders',
    command:  (event: MenuItemCommandEvent) => triggerDataUpdate(event, 'open')
  },
]

interface UpdateType extends MenuItem {
  label: string
  command: () => void
}

const defaultUpdateType: UpdateType = updateTypes[0] as UpdateType

// expansion control

const initExpandedKeys = (nodes: TreeNode[], levelsToExpans = 0): Record<string, boolean> => {
  const keys: Record<string, boolean> = {}
  const levelValue = levelsToExpans > 0
  nodes.forEach((node) => {
    keys[node.key] = levelValue
    if (node.children) {
      Object.assign(keys, initExpandedKeys(node.children, levelsToExpans - 1))
    }
  })
  keys['finished'] = false
  return keys
}

const changeExpansion = (nodes: TreeNode[], value: boolean) => {
  const changeExpansionRecursiveFuncion = (nodes: TreeNode[]): Record<string, boolean> => {
    const keys: Record<string, boolean> = {}
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

// analitics and stats

const monthsNodesUpToAlanitics = computed(() => {
  if (tree.value.length === 0) {
    return []
  }
  var allMonthsNodes: MonthNode[] = []
  tree.value.forEach((statusNode: StatusNode) => {
    allMonthsNodes = allMonthsNodes.concat(statusNode.children)
  })

  const res = allMonthsNodes.filter((monthNode) => {
    const monthDate = new Date(monthNode.data.date)
    if (monthDate >= analiticsStartDate.value! && monthDate <= analiticsEndDate.value!) {
      return monthNode
    }
  })
  if (!res) {
    return []
  }
  console.log(res)
  return res
})

const figureTypesCount = computed(() => {
  var typesCount: Record<string, { count: number, cost: number }> = {
    TOTAL: { count: 0, cost: 0 },
  }
  monthsNodesUpToAlanitics.value.forEach((monthNode) => {
    monthNode.children.forEach((orderNode) => {
      orderNode.children.forEach((itemNode) => {
        var type: string
        const scaleMatch = itemNode.data.name.match(/1\/\d{1,2}/)
        if (scaleMatch) {
          type = `${scaleMatch[0]} scale`
        } else if (itemNode.data.name.includes('Nendoroid')) {
          type = 'nendoroid'
        } else if (itemNode.data.scode.includes('GOODS')) {
          type = 'goods'
        } else {
          type = 'other'
        }
        if (!typesCount[type]) {
          typesCount[type] = { count: 0, cost: 0 }
        }
        typesCount[type].count++
        typesCount[type].cost += itemNode.data.price

        typesCount['TOTAL'].count++
        typesCount['TOTAL'].cost += itemNode.data.price
      })
    })
  })

  typesCount = Object.keys(typesCount)
    .sort((a, b) => (a === 'TOTAL' ? 1 : b === 'TOTAL' ? -1 : a.localeCompare(b)))
    .reduce((acc, key) => {
      acc[key] = typesCount[key]
      return acc
    }, {} as Record<string, { count: number, cost: number }>)

  return typesCount
})

const totalRowStyle = (data: [string, { count: number, cost: number }]) => {
  if (data[0] === 'TOTAL') {
    return {
      'font-weight': 'bold',
    }
  }
}

// chart

const costPerMonth = computed(() => {
  const costPerMonth: Record<string, number> = {}
  const allMonths = new Set<string>()
  const startDate = new Date(analiticsStartDate.value!)
  const endDate = new Date(analiticsEndDate.value!)

  for (let d = startDate; d <= endDate; d.setMonth(d.getMonth() + 1)) {
    const monthStr = d.toISOString().slice(0, 7)
    allMonths.add(monthStr)
  }

  allMonths.forEach((monthStr) => {
    costPerMonth[monthStr] = 0
  })
  monthsNodesUpToAlanitics.value.forEach((monthNode) => {
    monthNode.children.forEach((order) => {
      const monthStr = order.data.date.slice(0, 7)
      costPerMonth[monthStr] += order.data.price
    })
  })
  return Object.keys(costPerMonth)
    .sort()
    .reduce((acc, key) => {
      acc[key] = costPerMonth[key]
      return acc
    }, {} as Record<string, number>)
})

watch(costPerMonth, async () => {
  createChart(
    (document.getElementById('costPerMonthChart') as HTMLCanvasElement).getContext('2d')!,
    costPerMonth.value
  )
})

let chartInstance: Chart | null = null;

const createChart = (ctx: CanvasRenderingContext2D, data: Record<string, number>) => {
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
          backgroundColor: Object.keys(data).map((date) => {
            const monthDate = new Date(date);
            if (monthDate >= current_month) {
              return '#34d399'; // green pre-orders
            } else  {
              return 'gray'; // red shipped
            }
          }),
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
              const yenMax = this.chart.scales.y.max;
              const usdValue = (value as number) * yenMax * yenToUsd;
              return Math.round(usdValue).toLocaleString();
            },
          },
        },
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: function (context) {
              const yenValue = context.raw as number
              const usdValue = Math.round(yenValue * yenToUsd).toLocaleString()
              return `${yenValue.toLocaleString()}¥ / ${usdValue}$`
            },
          },
        },
      },
    },
  })
}

// basic data retrival and transformation

const getOrdersData = async (orderType = 'all'): Promise<Order[]> => {
  try {
    const response = await axios({
      method: 'get',
      url: '/api/orders/',
      params: {
        order_type: orderType,
      },
    })
    return response.data
  } catch (e) {
    console.error(e)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: `Failed to fetch data: ${e}`,
    })
    return []
  }
}

const postUpdateDataRequest = async (orderType: string): Promise<Order[]> => {
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
      severity: 'error',
      summary: 'Error',
      detail: `Failed to update data: ${e}`,
    })
    return []
  }
}

const triggerDataUpdate = async (event: MenuItemCommandEvent, orderType = 'current_month') => {
  loading.value = true
  try {
    await postUpdateDataRequest(orderType)
    await prepareData()
  } finally {
    loading.value = false
  }
}

const ordersDataToTree = (data: Data): TreeNode[] => {
  const activeOrdersNode: StatusNode = {
    key: 'active',
    data: {
      date: '',
      price: 0,
      amount: 0,
      in_stock_flag: true,
    },
    children: [],
  }

  const finishedOrdersNode: StatusNode = {
    key: 'finished',
    data: {
      date: '',
      price: 0,
      amount: 0,
      in_stock_flag: true,
    },
    children: [],
  }

  for (const [date_str, monthOrders] of Object.entries(data.by_month)) {
    const date = new Date(date_str)
    const monthNode: MonthNode = {
      key: `${date.toLocaleString('en', { month: 'long' })} ${date.getFullYear()} `,
      data: {
        date: date_str,
        price: 0,
        amount: 0,
        in_stock_flag: true,
      },
      children: monthOrders.map((order) => {
        const orderNode: OrderNode = {
          key: order.id,
          data: order,
          children: order.items.map((item) => {
            const itemNode: ItemNode = {
              key: item.id,
              data: item,
            }
            return itemNode
          }),
        }
        orderNode.data.amount = orderNode.children.reduce(
          (acc, item) => acc + item.data.amount,
          0
        )
        orderNode.data.in_stock_flag = orderNode.children.every(
          (item) => item.data.in_stock_flag
        )
        return orderNode
      }),
    }

    monthNode.data.price = monthNode.children.reduce(
      (acc, order) => acc + order.data.price,
      0
    )
    monthNode.data.amount = monthNode.children.reduce(
      (acc, order) => acc + order.data.amount,
      0
    )
    monthNode.data.in_stock_flag = monthNode.children.every(
      (order) => order.data.in_stock_flag
    )

    if (date >= data.oldestActiveOrderDate!) {
      activeOrdersNode.children.push(monthNode)
    } else {
      finishedOrdersNode.children.push(monthNode)
    }
  }

  [activeOrdersNode, finishedOrdersNode].forEach((node) => {
    node.data.price = node.children.reduce(
      (acc, month) => acc + month.data.price,
      0
    )
    node.data.amount = node.children.reduce(
      (acc, month) => acc + month.data.amount,
      0
    )
    node.data.in_stock_flag = node.children.every(
      (month) => month.data.in_stock_flag
    )
    node.data.date = node.children[0].data.date // just for sorting
    node.children.sort((a, b) => new Date(a.data.date).getTime() - new Date(b.data.date).getTime())
  })

  return [finishedOrdersNode, activeOrdersNode]
}

const parseOrdersData = (ordersData: Order[]): Data => {
  const by_month: Record<string, Order[]> = {}
  const by_status: Record<string, Order[]> = {}
  var dataStartDate: Date = new Date()
  var dataEndDate: Date = new Date()
  var oldestActiveOrderDate: Date = new Date()

  ordersData.map((order) => {
    const date_str = order.date
    const date = new Date(date_str)

    by_month[date_str] = by_month[date_str] || []
    by_month[date_str].push(order)

    const status = current_month <= date ? 'active' : 'finished'
    by_status[status] = by_status[status] || []
    by_status[status].push(order)

    if (dataStartDate === null || date < dataStartDate) {
      dataStartDate = date
    }
    if (dataEndDate === null || date > dataEndDate) {
      dataEndDate = date
    }
    if (status === 'active' && (oldestActiveOrderDate === null || date < oldestActiveOrderDate)) {
      oldestActiveOrderDate = date
    }
    return order
  })

  return {
    by_month,
    by_status,
    orders: ordersData,
    startDate: dataStartDate,
    endDate: dataEndDate,
    oldestActiveOrderDate,
  }
}

const prepareData = async () => {
  ordersData = await getOrdersData()
  data = parseOrdersData(ordersData)
  tree.value = ordersDataToTree(data)
  expandedKeys.value = initExpandedKeys(tree.value, 2)
  dataStartDate.value = data.startDate
  dataEndDate.value = data.endDate
  analiticsStartDate.value = data.oldestActiveOrderDate
  analiticsEndDate.value = data.endDate
}

// hooks

onMounted(async () => {
  await prepareData()
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

.p-treetable-tbody > tr[aria-level='3'] {
  background-color: black;
  color: white;
}
.p-treetable-tbody > tr[aria-level='4'] {
  background-color: black;
  color: white;
}

.p-treetable-tbody > tr[aria-level='2'] > td.dim {
  color: grey;
}

.p-treetable-tbody > tr[aria-level='4'] > td.dim {
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
.dataSelectorContainer {
  display: flex;
  gap: 20px;
  margin-bottom: 1rem;
}
</style>
