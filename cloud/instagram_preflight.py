"""Read-only account/connection check on the cloud runner. No media download/post."""
import os
import requests

def main():
    token = os.environ.get('IG_ACCESS_TOKEN')
    if not token:
        raise RuntimeError('Instagram credential missing; existing account reconnect required')
    headers = {'Authorization': 'Bearer ' + token}
    base = 'https://graph.instagram.com/v26.0'
    def get(path, params):
        response = requests.get(base + path, params=params, headers=headers,
                                timeout=40, allow_redirects=False)
        if not response.ok:
            error = response.json().get('error', {})
            raise RuntimeError('Instagram connection HTTP %s / code %s / subcode %s' %
                               (response.status_code, error.get('code'), error.get('error_subcode')))
        return response.json()
    identity = get('/me', {'fields': 'username'})
    if identity.get('username') != 'nordic_log':
        raise RuntimeError('Wrong account; no publication attempted')
    # No account metadata, tokens, media list or quota is persisted or emitted.
    print('Expected account authentication verified; no publication attempted')

if __name__ == '__main__':
    main()
