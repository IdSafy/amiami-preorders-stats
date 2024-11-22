<template>
  <div class="mainContainer">


  <div class="buttonContainer">
    
    <Button @click="triggerDataUpdate" label="Update" />
    <Button @click="expandAll" label="Expand all" />
    <Button @click="collapseAll" label="Collapse all" />
  </div>
  <Panel>
  <TreeTable 
  v-model:expandedKeys="expandedKeys" 
  :resizableColumns="false"
  :value="tree" 
  class="mt-6" 
  tableStyle="min-width: 10rem">
  <Column sortField="date" sortable expander style="width: 13rem;">
    <template #body="{ node }">
      <a :href="node.data.page_link">{{ node.key }}</a>
    </template>
  </Column>
  <Column field="amount" header="Amount" class="dim right" style="width: 5rem;"></Column>
  <Column header="Cost (¥)" class="dim price right" >
    <template #body="{ node }">
      {{ node.data.price.toLocaleString() + " ¥"}}
    </template>
  </Column>
  <Column header="Cost ($)"  class="dim price right" >
    <template #body="{ node }">
      {{ (node.data.price * yenToUsd).toLocaleString() + " $" }}
    </template>
  </Column>
  <Column header="In stock" class="dim right" style="width: 6rem;">
    <template #body="{ node }">
      <span :class="{ 'in-stock': node.data.in_stock_flag, 'out-of-stock': !node.data.in_stock_flag }">
        {{ node.data.in_stock_flag ? '✔️' : '❌' }}
      </span>
    </template>
  </Column>
  <Column  header="Name" field="name" style="width: auto;">
    
  </Column>
  </TreeTable>
  </Panel>
<Panel class="analytics">
  <template #header>
    <h3>Analytics</h3>
  </template>
  <Panel header="basic stats" toggleable class="basicAnalitics">
    <DataTable id="byTypeDataTable" :value="Object.entries(figureTypesCount)" size="small" style="text-align: right;" :row-style="totalRowStyle">
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
  </Panel >
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
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';

import Button from 'primevue/button';
import Column from 'primevue/column';
import DataTable from 'primevue/datatable';
import Divider from 'primevue/divider';
import Panel from 'primevue/panel';
import ProgressSpinner from 'primevue/progressspinner';
import TreeTable from 'primevue/treetable';

import Chart from 'chart.js/auto';
Chart.defaults.color = "#fff";

const yenToUsd = 0.0065

const loading = ref(false)

// expansion control

const initExpandedKeys = (nodes, levelValue = true) => {
  const keys = {};
  nodes.forEach(node => {
    keys[node.key] = levelValue;
    if (node.children) {
      Object.assign(keys, initExpandedKeys(node.children, false));
    }
  });
  return keys;
};

const changeExpansion = (nodes, value) =>{
  const changeExpansionRecursiveFuncion = (nodes) => {
    const keys = {};
    nodes.forEach(node => {
      keys[node.key] = value;
      if (node.children) {
        Object.assign(keys, changeExpansionRecursiveFuncion(node.children));
      }
    });
    return keys;
  };
  
  expandedKeys.value = changeExpansionRecursiveFuncion(tree.value);
}

const expandAll = () => {
  changeExpansion(tree.value, true);
};

const collapseAll = () => {
  changeExpansion(tree.value, false);
};

// stats

const figureTypesCount = computed(() => {
  var typesCount = {};
  ordersData.forEach(order => {
    order.items.forEach(item => {
      var type;
      const scaleMatch = item.name.match(/1\/\d{1,2}/);
      if (scaleMatch) {
        type = `${scaleMatch[0]} scale`;
      } else if (item.name.includes('Nendoroid')) {
        type = 'nendoroid';
      } else if (item.scode.includes('GOODS')) {
        type = 'goods';
      } else {
        type = 'other';
      }
      if (!typesCount[type]) {
        typesCount[type] = { count: 0, cost: 0 };
      }
      typesCount[type].count++;
      typesCount[type].cost += item.price;
    });
  });
  
  typesCount = Object.keys(typesCount).sort().reduce((acc, key) => {
    acc[key] = typesCount[key];
    return acc;
  }, {});
  typesCount['TOTAL'] = {
    count: ordersData.reduce((acc, order) => acc + order.items.length, 0),
    cost: ordersData.reduce((acc, order) => acc + order.price, 0)
  };

  return typesCount
});


const totalRowStyle = (data) => {
  if (data[0] === 'TOTAL') {
    return { 
      'font-weight': 'bold' ,
    };
  }
}; 

// chart

const costPerMonth = computed(() => {
  const costByMonth = {};
  const allMonths = new Set();
  const startDate = new Date(Math.min(...ordersData.map(order => new Date(order.date))));
  const endDate = new Date(Math.max(...ordersData.map(order => new Date(order.date))));
  
  for (let d = startDate; d <= endDate; d.setMonth(d.getMonth() + 1)) {
    const month = d.toISOString().slice(0, 7);
    allMonths.add(month);
  }
  
  allMonths.forEach(month => {
    costByMonth[month] = 0;
  });
  ordersData.forEach(order => {
    const month = order.date.slice(0, 7);
    costByMonth[month] += order.price;
  });
  
  return Object.keys(costByMonth).sort().reduce((acc, key) => {
    acc[key] = costByMonth[key];
    return acc;
  }, {});
});

const createChart = (ctx, data) => {
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: Object.keys(data),
      datasets: [
        {
        label: 'cost per month',
        data: Object.values(data),
        backgroundColor: '#34d399',
        borderWidth: 0,
        yAxisID: 'y'
      }
      ]
    },
    options: {
      scales: {
        y: {
          beginAtZero: true,
          position: 'left',
          title: {
            display: true,
            text: 'Cost (¥)'
          }
        },
        y1: {
          beginAtZero: true,
          position: 'right',
          title: {
            display: true,
            text: 'Cost ($)'
          },
          grid: {
            drawOnChartArea: false
          },
          ticks: {
            callback: function(value) {
              return (value * yenToUsd * this.chart.scales.y.max).toLocaleString();
            }
          }
        }
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: function(context) {
              const yenValue = context.raw;
              const usdValue = (yenValue * yenToUsd).toLocaleString();
              return `${yenValue.toLocaleString()}¥ / ${usdValue}$`;
            }
          }
        }
      }
    }
  });
}

// basic data retrival and transformation

const ordersData = [
{
  "id": "228471080",
  "status": "Pre-Order",
  "date": "2025-12-01",
  "price": 34980,
  "items": [
  {
    "id": "228471080_0",
    "scode": "FIGURE-177370",
    "name": "[AmiAmi Exclusive Bonus] [Exclusive Sale] Arknights Dusk 1/7 Complete Figure(Pre-order)(Single Shipment)",
    "thumb_url": "/images/product/thumb300/244/FIGURE-177370.jpg",
    "date": "2025-12-01",
    "price": 34980,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-177370"
  }
  ],
  "is_open": true,
  "page_link": "https://secure.amiami.com/eng/bill/2?d_no=228471080"
},
{
  "id": "228387570",
  "status": "Pre-Order",
  "date": "2025-09-01",
  "price": 22000,
  "items": [
  {
    "id": "228387570_0",
    "scode": "FIGURE-177575",
    "name": "Hatsune Miku Wa-Bunny 1/7 Scale Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/244/FIGURE-177575.jpg",
    "date": "2025-09-01",
    "price": 22000,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-177575"
  }
  ],
  "is_open": true,
  "page_link": "https://secure.amiami.com/eng/bill/2?d_no=228387570"
},
{
  "id": "753137142",
  "status": "Pre-order",
  "date": "2025-02-01",
  "price": 6570,
  "items": [
  {
    "id": "228018191_0",
    "scode": "FIGURE-175886",
    "name": "Nendoroid Blue Archive Asuna Ichinose(Pre-order)",
    "thumb_url": "/images/product/thumb300/243/FIGURE-175886.jpg",
    "date": "2025-02-01",
    "price": 6570,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-175886"
  }
  ],
  "is_open": true,
  "page_link": "https://secure.amiami.com/eng/bill/2?d_no=753137142"
},
{
  "id": "753137093",
  "status": "Pre-order",
  "date": "2025-01-01",
  "price": 53280,
  "items": [
  {
    "id": "225714940_0",
    "scode": "FIGURE-165893",
    "name": "[Bonus] Fushigi no Muyuutan -Yume iri no Jikan- Alice Liddell 1/7 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/241/FIGURE-165893.jpg",
    "date": "2025-01-01",
    "price": 23200,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-165893"
  },
  {
    "id": "228117157_0",
    "scode": "FIGURE-176244",
    "name": "[Exclusive Sale] Bunny Girl Aileen Sunkissed Ver. 1/12 Complete Model Action Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/244/FIGURE-176244.jpg",
    "date": "2025-01-01",
    "price": 6050,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-176244"
  },
  {
    "id": "228267369_0",
    "scode": "FIGURE-173173",
    "name": "ARTFX J NieR:Automata Ver1.1a 2B 1/8 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/243/FIGURE-173173.jpg",
    "date": "2025-01-01",
    "price": 24030,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-173173"
  }
  ],
  "is_open": true,
  "page_link": "https://secure.amiami.com/eng/bill/2?d_no=753137093"
},
{
  "id": "228281438",
  "status": "Pre-Order",
  "date": "2024-12-01",
  "price": 63140,
  "items": [
  {
    "id": "225870797_0",
    "scode": "FIGURE-166471",
    "name": "\"Date A Live\" Kurumi Tokisaki -Hanfu ver.- 1/7 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/241/FIGURE-166471.jpg",
    "date": "2024-12-01",
    "price": 38500,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-166471"
  },
  {
    "id": "226197434_0",
    "scode": "FIGURE-168099",
    "name": "[Bonus] Cirno illustration by Uuzan 1/7 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/241/FIGURE-168099.jpg",
    "date": "2024-12-01",
    "price": 20350,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-168099"
  },
  {
    "id": "228281438_0",
    "scode": "GOODS-04545504",
    "name": "Made in Abyss The Golden City of the Scorching Sun Abyss Map Ribbed Long Sleeve T-shirt /BLACK-M(Pre-order)",
    "thumb_url": "/images/product/thumb300/244/GOODS-04545504.jpg",
    "date": "2024-12-01",
    "price": 4290,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=GOODS-04545504"
  }
  ],
  "is_open": true,
  "page_link": "https://secure.amiami.com/eng/bill/2?d_no=228281438"
},
{
  "id": "228308247",
  "status": "Pre-Order",
  "date": "2025-05-01",
  "price": 24130,
  "items": [
  {
    "id": "228264797_0",
    "scode": "FIGURE-176944",
    "name": "Witch Hat Atelier Coco 1/8 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/244/FIGURE-176944.jpg",
    "date": "2025-05-01",
    "price": 18280,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-176944"
  },
  {
    "id": "228308247_0",
    "scode": "FIGURE-177139",
    "name": "Nendoroid Kizumonogatari Kiss-Shot Acerola-Orion Heart-Under-Blade(Pre-order)",
    "thumb_url": "/images/product/thumb300/244/FIGURE-177139.jpg",
    "date": "2025-05-01",
    "price": 5850,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-177139"
  }
  ],
  "is_open": true,
  "page_link": "https://secure.amiami.com/eng/bill/2?d_no=228308247"
},
{
  "id": "228514670",
  "status": "Pre-order",
  "date": "2025-07-01",
  "price": 57200,
  "items": [
  {
    "id": "228253957_0",
    "scode": "FIGURE-176776",
    "name": "[Exclusive Sale] Overlord Albedo 1/7 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/244/FIGURE-176776.jpg",
    "date": "2025-07-01",
    "price": 34800,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-176776"
  },
  {
    "id": "228514670_0",
    "scode": "FIGURE-177849",
    "name": "[Bonus] Rabbit Flova 1/7 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/244/FIGURE-177849.jpg",
    "date": "2025-07-01",
    "price": 22400,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-177849"
  }
  ],
  "is_open": true,
  "page_link": "https://secure.amiami.com/eng/bill/2?d_no=228514670"
},
{
  "id": "228552722",
  "status": "Pre-order",
  "date": "2026-01-01",
  "price": 41600,
  "items": [
  {
    "id": "228185100_0",
    "scode": "FIGURE-176593",
    "name": "[Bonus] Azur Lane Le Malin Mercredi at the Secret Base Ver. 1/6 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/244/FIGURE-176593.jpg",
    "date": "2026-01-01",
    "price": 19200,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-176593"
  },
  {
    "id": "228552722_0",
    "scode": "FIGURE-178510",
    "name": "Reverse: 1999 Sonetto 1/7 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/244/FIGURE-178510.jpg",
    "date": "2026-01-01",
    "price": 22400,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-178510"
  }
  ],
  "is_open": true,
  "page_link": "https://secure.amiami.com/eng/bill/2?d_no=228552722"
},
{
  "id": "228508402",
  "status": "Pre-order",
  "date": "2025-06-01",
  "price": 66460,
  "items": [
  {
    "id": "228145996_0",
    "scode": "FIGURE-172864",
    "name": "Steins;Gate Kurisu Makise - Reading Steiner 1/7 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/243/FIGURE-172864.jpg",
    "date": "2025-06-01",
    "price": 35800,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-172864"
  },
  {
    "id": "228387576_0",
    "scode": "FIGURE-177639",
    "name": "[Exclusive Sale] Kill la Kill Ryuko Matoi Kamui Senketsu ver. 1/8 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/244/FIGURE-177639.jpg",
    "date": "2025-06-01",
    "price": 16800,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-177639"
  },
  {
    "id": "228450253_0",
    "scode": "FIGURE-177843",
    "name": "Gift+ Honkai: Star Rail Kafka: Star Rail LIVE ver. 1/8 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/244/FIGURE-177843.jpg",
    "date": "2025-06-01",
    "price": 7110,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-177843"
  },
  {
    "id": "228508402_0",
    "scode": "FIGURE-178264",
    "name": "Nendoroid Genshin Impact Raiden Shogun(Pre-order)",
    "thumb_url": "/images/product/thumb300/244/FIGURE-178264.jpg",
    "date": "2025-06-01",
    "price": 6750,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-178264"
  }
  ],
  "is_open": true,
  "page_link": "https://secure.amiami.com/eng/bill/2?d_no=228508402"
},
{
  "id": "228185156",
  "status": "Pre-order",
  "date": "2025-02-01",
  "price": 70860,
  "items": [
  {
    "id": "227532522_0",
    "scode": "FIGURE-171959",
    "name": "KDcolle FALSLANDER RONIN 1/7 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/242/FIGURE-171959.jpg",
    "date": "2025-02-01",
    "price": 21780,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-171959"
  },
  {
    "id": "227947029_0",
    "scode": "FIGURE-175506",
    "name": "\"Eve HAND CUFFS ver.\" illustration by rurudo 1/6 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/243/FIGURE-175506.jpg",
    "date": "2025-02-01",
    "price": 20480,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-175506"
  },
  {
    "id": "228185156_0",
    "scode": "FIGURE-161654",
    "name": "[AmiAmi Exclusive Bonus] PRISMA WING Flower Imitation. Flower. Illustration by neco 1/7 Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/234/FIGURE-161654.jpg",
    "date": "2025-02-01",
    "price": 28600,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-161654"
  }
  ],
  "is_open": true,
  "page_link": "https://secure.amiami.com/eng/bill/2?d_no=228185156"
},
{
  "id": "227532523",
  "status": "Pre-Order",
  "date": "2025-12-01",
  "price": 32800,
  "items": [
  {
    "id": "227532523_0",
    "scode": "FIGURE-171858",
    "name": "Character Vocal Series 01 Hatsune Miku feat. Yoneyama Mai 1/7 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/242/FIGURE-171858.jpg",
    "date": "2025-12-01",
    "price": 32800,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-171858"
  }
  ],
  "is_open": true,
  "page_link": "https://secure.amiami.com/eng/bill/2?d_no=227532523"
},
{
  "id": "227973135",
  "status": "Pre-order",
  "date": "2025-03-01",
  "price": 92850,
  "items": [
  {
    "id": "226776801_0",
    "scode": "FIGURE-170565",
    "name": "My Dress-Up Darling Marin Kitagawa Liz Ver. 1/6 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/242/FIGURE-170565.jpg",
    "date": "2025-03-01",
    "price": 26960,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-170565"
  },
  {
    "id": "227798391_0",
    "scode": "FIGURE-172892",
    "name": "HORROR BISHOUJO Sadako 1/7 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/243/FIGURE-172892.jpg",
    "date": "2025-03-01",
    "price": 18810,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-172892"
  },
  {
    "id": "227875621_0",
    "scode": "FIGURE-171756",
    "name": "OVERLORD Albedo 10th Anniversary so-bin ver.(Pre-order)",
    "thumb_url": "/images/product/thumb300/242/FIGURE-171756.jpg",
    "date": "2025-03-01",
    "price": 22770,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-171756"
  },
  {
    "id": "227973135_0",
    "scode": "FIGURE-175366",
    "name": "TV Anime \"Call of the Night\" Nazuna Nanakusa 1/7 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/243/FIGURE-175366.jpg",
    "date": "2025-03-01",
    "price": 24310,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-175366"
  }
  ],
  "is_open": true,
  "page_link": "https://secure.amiami.com/eng/bill/2?d_no=227973135"
},
{
  "id": "226594597",
  "status": "Pre-Order",
  "date": "2025-05-01",
  "price": 15800,
  "items": [
  {
    "id": "226594597_0",
    "scode": "FIGURE-170041",
    "name": "Xenoblade Chronicles 3 Mio 1/7 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/242/FIGURE-170041.jpg",
    "date": "2025-05-01",
    "price": 15800,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-170041"
  }
  ],
  "is_open": true,
  "page_link": "https://secure.amiami.com/eng/bill/2?d_no=226594597"
},
{
  "id": "228297525",
  "status": "Pre-order",
  "date": "2025-04-01",
  "price": 86270,
  "items": [
  {
    "id": "226594598_0",
    "scode": "FIGURE-167993",
    "name": "Blue Archive Yuuka -Daily Life Of A Treasurer- 1/7 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/241/FIGURE-167993.jpg",
    "date": "2025-04-01",
    "price": 18900,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-167993"
  },
  {
    "id": "227961283_0",
    "scode": "FIGURE-175715",
    "name": "[Bonus] Touhou Project Ghost From the Calamitous Nirvana Yuyuko Saigyouji 1/6 Complete Figure Deluxe Edition(Pre-order)",
    "thumb_url": "/images/product/thumb300/243/FIGURE-175715.jpg",
    "date": "2025-04-01",
    "price": 26140,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-175715"
  },
  {
    "id": "228018192_0",
    "scode": "FIGURE-175895",
    "name": "[Bonus] Arknights W Dress Ver. 1/7 Complete Figure(Pre-order)",
    "thumb_url": "/images/product/thumb300/243/FIGURE-175895.jpg",
    "date": "2025-04-01",
    "price": 15090,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-175895"
  },
  {
    "id": "228297525_0",
    "scode": "FIGURE-174682",
    "name": "[Bonus] Touhou Project Eternal Shrine Maiden Reimu Hakurei 1/6 Complete Figure Deluxe Edition(Pre-order)",
    "thumb_url": "/images/product/thumb300/243/FIGURE-174682.jpg",
    "date": "2025-04-01",
    "price": 26140,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-174682"
  }
  ],
  "is_open": true,
  "page_link": "https://secure.amiami.com/eng/bill/2?d_no=228297525"
},
{
  "id": "228407216",
  "status": "Provisional preorder",
  "date": "2024-11-01",
  "price": 37840,
  "items": [
  {
    "id": "226235788_0",
    "scode": "FIGURE-168413",
    "name": "Nendoroid Gushing over Magical Girls Magia Baiser(Pre-order)",
    "thumb_url": "/images/product/thumb300/242/FIGURE-168413.jpg",
    "date": "2024-11-01",
    "price": 6480,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-168413"
  },
  {
    "id": "228177696_0",
    "scode": "FIGURE-164693",
    "name": "Thunderbolt Squad Vodka Mirror 1/9 Seamless Action Figure(Provisional Pre-order)",
    "thumb_url": "/images/product/thumb300/241/FIGURE-164693.jpg",
    "date": "2024-11-01",
    "price": 15400,
    "amount": 1,
    "in_stock_flag": 0,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-164693"
  },
  {
    "id": "228407216_0",
    "scode": "FIGURE-151614-R015",
    "name": "(Pre-owned ITEM:A/BOX:B)POP UP PARADE Knights of Sidonia: Love Woven in the Stars Tsumugi Shiraui L Complete Figure(Released)",
    "thumb_url": "/images/product/thumb300/231/FIGURE-151614.jpg",
    "date": "2023-07-01",
    "price": 13980,
    "amount": 1,
    "in_stock_flag": 1,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-151614-R015"
  },
  {
    "id": "228407216_1",
    "scode": "FIGURE-147217-R074",
    "name": "(Pre-owned ITEM:A/BOX:B)Hatsune Miku Noodle Stopper Figure -Villain Color Variation ver.- (Game-prize)(Released)",
    "thumb_url": "/images/product/thumb300/224/FIGURE-147217.jpg",
    "date": "2022-09-01",
    "price": 1980,
    "amount": 1,
    "in_stock_flag": 1,
    "page_link": "https://www.amiami.com/eng/detail?scode=FIGURE-147217-R074"
  }
  ],
  "is_open": true,
  "page_link": "https://secure.amiami.com/eng/bill/2?d_no=228407216"
}
]

const getOrdersData = async () => {
  return ordersData
}

const updateData = async () =>  {
  const new_data = await getOrdersData()
  ordersData.splice(0, ordersData.length, ...new_data)
  triggerDataUpdate()
}

const triggerDataUpdate = async () => {
  loading.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 2000));
    await updateData()
    tree.value = ordersDataToTree(await getOrdersData())
  } finally {
    loading.value = false
  }
}

const ordersDataToTree = (ordersData) => {
  const orders_as_tree = ordersData.map(order => {
    const order_node = {
      key: order.id,
      data: order,
      children: order.items.map(item => {
        const item_note = {
          key: item.id,
          data: item
        }
        item_note.amount = item.amount
        return item_note
      })
    }
    // order_node.data.name = order_node.data.id
    order_node.data.amount = order_node.children.reduce((acc, item) => acc + item.data.amount, 0)
    order_node.data.in_stock_flag = order_node.children.every(item => item.data.in_stock_flag)
    return order_node
  })
  
  const by_release_dates = {}
  
  for (const order of orders_as_tree) {
    const date = order.data.date
    by_release_dates[date] = by_release_dates[date] || []
    by_release_dates[date].push(order)
  }
  
  const treeData = Object.keys(by_release_dates).map(date => {
    const month_node = {
      key: date,
      data: {
        date: date,
      },
      children: by_release_dates[date]
    }
    month_node.data.price = by_release_dates[date].reduce((acc, order) => acc + order.data.price, 0)
    month_node.data.amount = month_node.children.reduce((acc, order) => acc + order.data.amount, 0)
    month_node.data.in_stock_flag = month_node.children.every(order => order.data.in_stock_flag)
    return month_node
  })
  return treeData.sort((a, b) => a.key < b.key ? -1 : 1)
}
const tree = ref(ordersDataToTree(ordersData))
const expandedKeys = ref(initExpandedKeys(tree.value))

onMounted(() => {
  createChart(document.getElementById('costPerMonthChart').getContext('2d'), costPerMonth.value);
});

</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}

.overlay {
  position: fixed;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  background-color: rgba(0,0,0,0.5);
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: center;
}

a {
  color: whitesmoke;
}

.p-treetable-tbody > tr[aria-level="2" ] {
  background-color: black;
  color: white;
}
.p-treetable-tbody > tr[aria-level="3"] {
  background-color: black;
  color: white;
}

.p-treetable-tbody > tr[aria-level="1"] > td.dim {
  color: grey;
}

.p-treetable-tbody > tr[aria-level="3"] > td.dim {
  color: grey;
}

.p-treetable-tbody > tr > td.right > div,
.p-treetable-thead > tr > th.right > div{  
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
.buttonContainer{
  display: flex;
  justify-content: center;
  margin-top: 20px;
  gap: 20px;
}
.mainContainer{
  display: flex;
  flex-flow: column;
  gap: 1rem;
}

#byTypeDataTable {
  width: 40%;
}
</style>
