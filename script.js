return fetch(
  "https://shopee.vn/api/v2/flash_sale/flash_sale_batch_get_items", {
    "headers": {
      "accept": "application/json",
      "accept-language": "vi",
      "content-type": "application/json",
      "if-none-match-": "55b03-c9b9fb25684b2b06733c64898f2b3197",
      "sec-fetch-dest": "empty",
      "sec-fetch-mode": "cors",
      "sec-fetch-site": "same-origin",
      "x-api-source": "rweb",
      "x-csrftoken": "A0O24HgbOXbamkLtd1BV8OVFrcXOwzjY",
      "x-kl-ajax-request": "Ajax_Request",
      "x-requested-with": "XMLHttpRequest",
      "x-shopee-language": "vi"
    },
    "referrer": "https://shopee.vn/flash_sale?categoryId="+catId+"&promotionId="+promoId,
    "referrerPolicy": "no-referrer-when-downgrade",
    "body": "{\"promotionid\":"+promoId+",\"categoryid\":"+catId+",\"itemids\":["+itemId+"],\"sort_soldout\":false,\"limit\":1,\"need_personalize\":true,\"with_dp_items\":true}",
    "method": "POST",
    "mode": "cors",
    "credentials": "include"
  }).then(res => res.json());
