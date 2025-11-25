> API contract
> 

## Endpoint:
- #### Login
- #### Customer List
- #### Customer Detail
<br>

### Login

- URL
    - /token
- Method
    - POST
- Request Body
    - username as string
    - password as string
- Contoh Response

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxxxx",
  "token_type": "bearer"
}
```

### Customers List

- URL
    - /
- Method
    - GET
- Headers:
    - Authorization: Bearer <access_token>
- Optional Query Parameters:
    - name: str → partial, case-insensitive match
    - min_age: int
    - max_age: int
    - page: int (default = 1)
    - page_size: int (default = 30, max = 100)
- Response
    
    ```json
    {
      "page": 1,
      "page_size": 30,
      "total": 127,
      "total_pages": 5,
      "items": [
    	  {
    	    "customer_id": 5001,
    	    "name": "Ricardo Mendes",
    	    "phone_number": "+351912345678",
    	    "age": 37,
    	    "contact_method": "cellular",
    	    "subscription_probability": null
    	  },
    	  {
    	    "customer_id": 5002,
    	    "name": "Carla Ferreira",
    	    "phone_number": "+351923456789",
    	    "age": 52,
    	    "contact_method": "telephone",
    	    "subscription_probability": null
    	  },
        ...
      ]
    }
    ```
    

### Customer Detail

- URL
    - /customers/{customer_id}
- Method
    - GET
- Headers:
    - Authorization: Bearer <access_token>
- Response

```json
{
  "customer_id": 5002,
  "name": "Carla Ferreira",
  "phone_number": "+351923456789",
  "age": 52,
  "job": "management",
  "marital_status": "married",
  "education": "professional.course",
  "has_default_credit": "unknown",
  "has_housing_loan": "yes",
  "has_personal_loan": "yes",
  "contact_method": "telephone",
  "last_contact_month": "jul",
  "last_contact_weekday": "mon",
  "last_call_duration_sec": 420,
  "current_campaign_contacts": 2,
  "days_since_last_campaign": 180,
  "previous_campaign_contacts": 1,
  "previous_campaign_outcome": "success",
  "employment_variation_rate": -0.1,
  "consumer_price_index": 93.2,
  "consumer_confidence_index": -42.5,
  "euribor_3m_rate": 4.965,
  "number_of_employed": 5228,
  "subscription_probability": null
}
```
