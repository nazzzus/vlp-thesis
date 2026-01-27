import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL;

export const options = {
    vus: 10,
    duration: '20s',
};

export default function () {
    const url = `${BASE_URL}/vehicles?limit=50`;

    const res = http.get(url, {
        headers: {
            'Accept': 'application/json',
        },
    });

    check(res, {
        'status is 200': (r) => r.status === 200,
        'response is not empty': (r) => r.body && r.body.length > 0,
    });

    sleep(0.1);
}
