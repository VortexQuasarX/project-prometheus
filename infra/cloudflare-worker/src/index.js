export default {
  async fetch(request) {
    const url = new URL(request.url);
    url.hostname = "4oyzp80sy9.execute-api.ap-south-1.amazonaws.com";
    url.protocol = "https:";

    const newHeaders = new Headers(request.headers);
    newHeaders.set("Host", "4oyzp80sy9.execute-api.ap-south-1.amazonaws.com");

    const newRequest = new Request(url.toString(), {
      method: request.method,
      headers: newHeaders,
      body: request.body,
      redirect: "follow",
    });

    return fetch(newRequest);
  },
};
