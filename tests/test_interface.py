def test_interface_e_arquivos_publicos(client):
    resposta = client.get('/interface')
    assert resposta.status_code == 200
    assert 'Acesse sua operação' in resposta.text
    assert resposta.headers['cache-control'] == 'no-store'
    for arquivo, trecho in [('app.js', '/auth/login'), ('style.css', '@media')]:
        resposta = client.get('/interface/arquivos/' + arquivo)
        assert resposta.status_code == 200
        assert trecho in resposta.text
    assert client.get('/').json()['mensagem'] == 'LogiFlow API está funcionando.'


def test_interface_nao_abre_acesso_aos_dados(client):
    assert client.get('/pedidos').status_code == 401
    assert client.get('/cargas').status_code == 401
    assert client.get('/dashboard/resumo').status_code == 401
