# n8n workflow: enrich inbound leads with GPT and push to HubSpot

**Budget:** Hourly, $35–50/h · **Duration:** 1 to 3 months · **Experience:** Intermediate

We get 150–200 inbound leads a month from our website form and LinkedIn ads. Right
now an SDR spends about an hour a day googling each company, guessing company size and
industry, and copying everything into HubSpot by hand. Half the leads sit untouched for
two days before anyone looks at them.

We want an n8n workflow (we already self-host n8n) that picks up every new lead,
researches the company with GPT or a similar model, scores it against our ideal
customer profile, and creates or updates the contact and company in HubSpot with the
enriched fields. Low-confidence results should be flagged for a human instead of being
written straight in.

**Screening questions**
1. Describe an n8n workflow you built that used an LLM. What did it do?
2. How would you stop the model from writing wrong data into our CRM?
