# Bing Custom Search Setup Guide

This guide walks you through setting up a Bing Custom Search instance that restricts the Ohio BMV agent's grounding to only approved, official sources.

## Overview

Bing Custom Search allows you to create a tailored search experience that:
- Only searches specified domains
- Boosts/demotes specific sites based on relevance
- Provides clean, focused results for the AI agent

For the Ohio BMV assistant, we restrict searches to official Ohio BMV and Ohio Revised Code websites to ensure accuracy and prevent hallucinations.

---

## Prerequisites

1. **Azure Subscription** with access to create Bing Custom Search resources
2. **Azure Portal access** or Azure CLI
3. **Bing Custom Search API** subscription

---

## Step 1: Create a Bing Custom Search Resource

### Via Azure Portal

1. Navigate to the [Azure Portal](https://portal.azure.com)
2. Click **Create a resource**
3. Search for **"Bing Custom Search"**
4. Click **Create**
5. Fill in the details:
   - **Subscription:** Your Azure subscription
   - **Resource Group:** Create new or use existing (e.g., `rg-ohio-bmv-foundry`)
   - **Name:** `ohio-bmv-custom-search`
   - **Pricing Tier:** S1 (Standard) or F0 (Free for testing)
   - **Location:** Choose a region close to your deployment
6. Click **Review + Create**, then **Create**

### Via Azure CLI

```bash
# Create resource group if needed
az group create --name rg-ohio-bmv-foundry --location eastus

# Create Bing Custom Search resource
az cognitiveservices account create \
  --name ohio-bmv-custom-search \
  --resource-group rg-ohio-bmv-foundry \
  --kind Bing.CustomSearch \
  --sku S1 \
  --location eastus \
  --yes
```

---

## Step 2: Get Your API Key

### Via Azure Portal

1. Navigate to your Bing Custom Search resource
2. Go to **Keys and Endpoint**
3. Copy **Key 1** or **Key 2**
4. Save this key securely (you'll need it for the Foundry agent configuration)

### Via Azure CLI

```bash
az cognitiveservices account keys list \
  --name ohio-bmv-custom-search \
  --resource-group rg-ohio-bmv-foundry
```

---

## Step 3: Configure Custom Search Instance

1. Navigate to the [Bing Custom Search Portal](https://www.customsearch.ai/)
2. Sign in with your Microsoft account
3. Click **New Instance** or **Create Instance**
4. Name your instance: `ohio-bmv-grounding-only`

### Configuration Tab

#### Active Sites (Include)

Add the following domains with **"Include subpages"** enabled:

```
https://www.bmv.ohio.gov/
https://codes.ohio.gov/ohio-revised-code
https://bmvonline.dps.ohio.gov/
https://www.bmv.ohio.gov/about-contact.aspx
https://bmv.ohio.gov/dl-identity-documents.aspx
```

**How to add:**
1. Click **Add** under "Active"
2. Paste the URL
3. Select **Include subpages**
4. Click **Add**

#### Rank Adjustments (Optional but Recommended)

To ensure official sources are prioritized:

1. Go to the **Ranking** tab
2. Add the following domains with **Boost**:
   - `www.bmv.ohio.gov` → **Boost**
   - `codes.ohio.gov` → **Boost**

#### Blocked Sites

Add any domains you want to explicitly block (optional):
- Social media sites
- Forum sites (Reddit, Quora, etc.)
- Non-official BMV information sites

---

## Step 4: Get Your Custom Configuration ID

1. In the Bing Custom Search Portal, go to your instance
2. Click on **Production** tab
3. Copy the **Custom Configuration ID** (looks like: `a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6`)
4. Save this ID - you'll need it for the Foundry agent

---

## Step 5: Test Your Custom Search

### Via REST API

```bash
curl -X GET \
  "https://api.bing.microsoft.com/v7.0/custom/search?q=Ohio+driver+license+renewal&customconfig=YOUR_CUSTOM_CONFIG_ID" \
  -H "Ocp-Apim-Subscription-Key: YOUR_API_KEY"
```

Replace:
- `YOUR_CUSTOM_CONFIG_ID` with your Custom Configuration ID from Step 4
- `YOUR_API_KEY` with your API key from Step 2

### Expected Response

You should see JSON results containing only pages from:
- `bmv.ohio.gov`
- `codes.ohio.gov`
- Other domains you specified

### Via Bing Custom Search Portal

1. Go to your instance in the portal
2. Click the **Test** tab
3. Enter a query like: `driver license address change`
4. Verify results only come from your specified domains

---

## Step 6: Connect to Azure AI Foundry Agent

### In Azure AI Foundry Studio

1. Navigate to your AI Foundry workspace
2. Go to your agent configuration
3. Under **Grounding**, add a new grounding source:
   - **Type:** Bing Custom Search
   - **API Key:** Your Bing Custom Search API key
   - **Custom Configuration ID:** Your Custom Configuration ID
   - **Name:** `Ohio BMV Official Sources`

4. Save the configuration

### Test in Foundry Playground

Try asking questions like:
- "What documents do I need to renew my Ohio driver's license?"
- "What are the Ohio BMV office hours?"
- "How much does it cost to get a duplicate license?"

The agent should:
- ✅ Only cite information from official BMV sources
- ✅ Include source links to `bmv.ohio.gov` or `codes.ohio.gov`
- ❌ Not reference forums, social media, or unofficial sites

---

## Step 7: Fine-Tune (Optional)

Based on testing, you can refine your configuration:

### Add More Specific Pages

If certain pages are particularly important:
```
https://www.bmv.ohio.gov/dl-new.aspx
https://www.bmv.ohio.gov/dl-renewal.aspx
https://www.bmv.ohio.gov/fees.aspx
```

### Adjust Ranking

- **Boost** frequently-referenced pages
- **Demote** less relevant sections (but keep them searchable)

### Add Synonyms (in Bing Custom Search Portal)

Help the search understand BMV-specific terminology:
- "DL" → "Driver License"
- "BMV" → "Bureau of Motor Vehicles"
- "OH|ID" → "Ohio Identification Card"

---

## Troubleshooting

### Issue: Agent cites non-official sources

**Solution:**
1. Verify your Custom Configuration ID is correct in Foundry
2. Check that "Include subpages" is enabled for all domains
3. Add problematic domains to the **Blocked** list

### Issue: No results returned

**Solution:**
1. Check your API key is valid and not expired
2. Verify domains are accessible (not behind logins)
3. Try broader queries in the test portal
4. Ensure you're using the **Production** endpoint, not Draft

### Issue: Results too narrow

**Solution:**
1. Add more specific subpages to Active sites
2. Reduce or remove rank demotions
3. Add related official Ohio government domains if needed

---

## Maintenance

### Regular Review

- **Monthly:** Review search logs in Bing Custom Search Portal
- **Quarterly:** Update blocked domains list based on agent responses
- **As needed:** Add new official BMV pages when they're published

### Updates

If Ohio BMV launches new official pages:
1. Add them to the Active sites list
2. Consider boosting them if they're high-priority
3. Test with relevant queries

---

## Cost Considerations

**Bing Custom Search Pricing (as of 2024):**

- **Free Tier (F0):** 1,000 queries/month
- **Standard (S1):** $3 per 1,000 queries

For a production deployment:
- Estimate 5-10 queries per agent conversation
- Monitor usage in Azure Portal
- Set up alerts at 80% of quota

---

## Security Best Practices

1. **Store API keys in Azure Key Vault**, not in code
2. **Rotate keys** every 90 days
3. **Use separate instances** for dev/test/prod
4. **Monitor usage** for anomalies
5. **Limit scope** to only necessary domains

---

## Additional Resources

- [Bing Custom Search Documentation](https://learn.microsoft.com/en-us/bing/search-apis/bing-custom-search/)
- [Azure AI Foundry Grounding](https://learn.microsoft.com/en-us/azure/ai-foundry/)
- [Bing Custom Search API Reference](https://learn.microsoft.com/en-us/rest/api/cognitiveservices-bingsearch/bing-custom-search-api-v7-reference)
