import os
from collections import defaultdict
from datetime import date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, jsonify, make_response
import pymysql
from werkzeug.utils import secure_filename
import random
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from io import BytesIO
import os
from collections import defaultdict
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
import os
from collections import defaultdict

app = Flask(__name__, static_folder='static')
app.template_folder = os.path.dirname(os.path.abspath(__file__))
app.secret_key = 'sua_chave_secreta_aqui'
UPLOAD_FOLDER = 'static/images/'  # Substitua pelo caminho real do seu diretório de uploads
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
data_criacao = date.today()  # Obtém a data atual

# Função para obter uma conexão de banco de dados por thread

def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(host='localhost', user='root', password='1234', db='acervo_receitas', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
    return g.db

# Função para fechar a conexão de banco de dados no final da solicitação
@app.teardown_appcontext
def close_db(error):
    if 'db' in g:
        g.db.close()

@app.before_request
def load_logged_in_user():
    db = get_db()
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        with db.cursor() as cursor:
            sql = "SELECT * FROM login WHERE id = %s"
            try:
                cursor.execute(sql, user_id)
                g.user = cursor.fetchone()
            except pymysql.Error as e:
                print("Erro ao executar a consulta SQL:", e)


# Decorator para verificar a autenticação do usuário
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    db = get_db()
    user_info = g.user
    if request.method == 'POST':
        # Processar o formulário de login
        username = request.form['username']
        password = request.form['password']

        with db.cursor() as cursor:
            sql = "SELECT * FROM login WHERE username = %s"
            cursor.execute(sql, (username))
            user = cursor.fetchone()
            if user and password:
                print('user id:', user['id'])
                # Login bem-sucedido, redirecionar para a página principal
                flash('Login bem-sucedido!', 'success')
                session['user_id'] = user['id']  # Salvar o ID do usuário na sessão
                return redirect(url_for('index'))  # Redirecionar para 'receitas'

            else:
                flash('Nome de usuário ou senha incorretos.', 'error')

    return render_template('templates/usuario/login.html', user_info=user_info)

@app.route('/logout')
def logout():
    # Remova a chave 'user_id' da sessão para deslogar o usuário
    session.pop('user_id', None)
    flash('Você foi deslogado com sucesso.', 'success')
    return redirect(url_for('login'))

@app.route('/esqueci_senha', methods=['GET', 'POST'])
def forgot_password():
    db = get_db()
    user_info = g.user
    if request.method == 'POST':
        email = request.form['email']

        with db.cursor() as cursor:
            sql = "SELECT * FROM login WHERE email = %s"
            cursor.execute(sql, (email,))
            user = cursor.fetchone()

            if user:
                # Crie um token de redefinição de senha e insira na tabela password_reset_tokens
                flash('Um email foi enviado com instruções para redefinir a senha.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Nenhum usuário encontrado com esse email.', 'error')

    return render_template('templates/usuario/forgot_password.html', user_info=user_info)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user_info = g.user
    if request.method == 'POST':
        new_password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Verifique o token de redefinição de senha e atualize a senha do usuário

        flash('Senha redefinida com sucesso.', 'success')
        return redirect(url_for('login'))

    return render_template('templates/usuario/reset_password.html', token=token, user_info=user_info)


@app.route('/cadastro_usuario', methods=['GET', 'POST'])
def signup():
    user_info = g.user
    db = get_db()
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        with db.cursor() as cursor:
            sql = "INSERT INTO login (username, password, email) VALUES (%s, %s, %s)"
            cursor.execute(sql, (username, password, email))
            db.commit()

        flash('Cadastro realizado com sucesso. Faça login para continuar.', 'success')
        return redirect(url_for('login'))

    return render_template('templates/usuario/signup.html', user_info=user_info)


def gerar_isbn():
    prefixo = "978"
    grupo_editorial = random.randint(10, 99)
    identificador_titulo = random.randint(1000, 9999)
    digito_verificador = random.randint(0, 9)

    isbn_formatado = f"{prefixo} - {grupo_editorial} - {identificador_titulo} - {digito_verificador}"
    return isbn_formatado


@app.route("/layout")
def layout():
    user_info = g.user
    return render_template('templates/layout.html', user_info=user_info)


@app.route("/usuario_page")
def usuario_page():
    # Obtenha as informações da conta do usuário atual (você já carregou o usuário atual em g.user no `before_request`)
    user_info = g.user  # Isso assume que você tem as informações do usuário na tabela 'login'

    return render_template('templates/usuario/usuario_page.html', user_info=user_info)


@app.route('/categorias_receitas_table')
def categorias_receitas_table():
    user_info = g.user
    db = get_db()

    search_query = request.args.get("search", "")  # Obtém o critério de busca do parâmetro de consulta

    with db.cursor() as cursor:
        if search_query:
            sql_categoria_receita = "SELECT * FROM categoria_receita WHERE categoria LIKE %s OR descricao LIKE %s"
            cursor.execute(sql_categoria_receita, ("%" + search_query + "%", "%" + search_query + "%"))
        else:
            sql_categoria_receita = "SELECT * FROM categoria_receita"
            cursor.execute(sql_categoria_receita)

        categorias = cursor.fetchall()

    return render_template('templates/tables/categorias_receitas_table.html', categorias=categorias,
                           user_info=user_info)


@app.route("/ingredientes_table")
def ingredientes_table():
    db = get_db()
    user_info = g.user
    search_query = request.args.get("search", "")  # Obtém o critério de busca do parâmetro de consulta

    with db.cursor() as cursor:
        if search_query:
            sql_ingrediente = "SELECT * FROM ingrediente WHERE nome LIKE %s"
            cursor.execute(sql_ingrediente, ("%" + search_query + "%"))
        else:
            sql_ingrediente = "SELECT * FROM ingrediente"  # Modificado aqui
            cursor.execute(sql_ingrediente)

        ingredientes = cursor.fetchall()

    return render_template('templates/tables/ingredientes_table.html', ingredientes=ingredientes, user_info=user_info)


@app.route("/medidas_table")
def medidas_table():
    db = get_db()
    user_info = g.user
    search_query = request.args.get("search", "")  # Obtém o critério de busca do parâmetro de consulta

    with db.cursor() as cursor:
        if search_query:
            sql_medida = "SELECT * FROM medida WHERE medida LIKE %s OR sigla LIKE %s"
            cursor.execute(sql_medida, ("%" + search_query + "%", "%" + search_query + "%"))
        else:
            sql_medida = "SELECT * FROM medida"  # Modificado aqui
            cursor.execute(sql_medida)

        medidas = cursor.fetchall()

    return render_template('templates/tables/medidas_table.html', medidas=medidas, user_info=user_info)


@app.route("/restaurantes_table")
def restaurantes_table():
    db = get_db()
    user_info = g.user
    search_query = request.args.get("search", "")  # Obtém o critério de busca do parâmetro de consulta

    with db.cursor() as cursor:
        if search_query:
            sql_restaurante = "SELECT * FROM restaurante WHERE nome LIKE %s OR contato LIKE %s OR fantasia LIKE %s"
            cursor.execute(sql_restaurante, ("%" + search_query + "%", "%" + search_query + "%", "%" + search_query + "%"))
        else:
            sql_restaurante = "SELECT * FROM restaurante"  # Modificado aqui
            cursor.execute(sql_restaurante)

        restaurantes = cursor.fetchall()

    return render_template('templates/tables/restaurantes_table.html', restaurantes=restaurantes, user_info=user_info)


@app.route("/cargos_table")
def cargos_table():
    db = get_db()
    user_info = g.user
    search_query = request.args.get("search", "")  # Obtém o critério de busca do parâmetro de consulta

    with db.cursor() as cursor:
        if search_query:
            # Modifique a consulta SQL para incluir a cláusula WHERE para a pesquisa
            sql_cargo = "SELECT * FROM cargo WHERE nome LIKE %s OR descricao LIKE %s " \
                        "OR data_inicio = %s OR data_fim = %s"
            search_query_with_wildcard = f"%{search_query}%"  # Adicione curingas aos lados do termo de busca
            cursor.execute(sql_cargo, (search_query_with_wildcard, search_query_with_wildcard, search_query, search_query))
        else:
            sql_cargo = "SELECT * FROM cargo"
            cursor.execute(sql_cargo)

        cargos = cursor.fetchall()

    return render_template('templates/tables/cargos_table.html', cargos=cargos, user_info=user_info)


@app.route("/funcionarios_table")
def funcionarios_table():
    db = get_db()
    user_info = g.user
    search_query = request.args.get("search")  # Obtém a consulta de pesquisa do campo de formulário

    with db.cursor() as cursor:
        if search_query:
            # Modifique a consulta SQL para incluir a cláusula WHERE para a pesquisa
            sql_funcionario = "SELECT * FROM funcionario WHERE nome LIKE %s OR rg LIKE %s OR salario LIKE %s " \
                              "OR nome_fantasia LIKE %s"
            cursor.execute(sql_funcionario, ("%" + search_query + "%", "%" + search_query + "%", "%" + search_query +
                                             "%", "%" + search_query + "%"))

        else:
            sql_funcionario = "SELECT * FROM funcionario"
            cursor.execute(sql_funcionario)

        funcionarios = cursor.fetchall()

    return render_template('templates/tables/funcionarios_table.html', funcionarios=funcionarios, user_info=user_info)

@app.route('/adicionar_nota/<int:id_receita>', methods=['POST'])
def adicionar_nota(id_receita):
    db = get_db()
    user_info = g.user

    if request.method == 'POST':
        nova_nota = request.form.get('nota')  # Supondo que a nota seja enviada via POST

        with db.cursor() as cursor:
            # Query para atualizar a nota na tabela de receitas onde o ID da receita corresponde ao fornecido
            query = "UPDATE receita SET nota = %s WHERE id_receita = %s"
            cursor.execute(query, (nova_nota, id_receita))

            # Commit da transação para salvar as alterações no banco de dados
            db.commit()

            return jsonify({'success': True, 'message': 'Nota atualizada com sucesso!'})

    return jsonify({'success': False, 'message': 'Método inválido'})


@app.route('/receita/<int:id>')
def receita(id):
    db = get_db()
    user_info = g.user

    # Consulta o banco de dados para obter os detalhes da receita com base no ID
    with db.cursor() as cursor:
        # Consulta para obter detalhes da receita
        sql_receita = "SELECT * FROM receita WHERE id_receita = %s"
        cursor.execute(sql_receita, (id,))
        receita = cursor.fetchone()

        # Consulta para obter ingredientes associados a essa receita
        sql_ingredientes = """
        SELECT ir.quantidade, m.sigla AS medida, i.nome AS ingrediente
        FROM ingredientes_receita ir
        INNER JOIN medida m ON ir.id_medida = m.id_medida
        INNER JOIN ingrediente i ON ir.id_ingrediente = i.id_ingrediente
        WHERE ir.id_receita = %s
        """

        cursor.execute(sql_ingredientes, (id,))
        ingredientes = cursor.fetchall()
        print(ingredientes)
    if receita is None:
        # Lidar com o caso em que a receita não foi encontrada
        return "Receita não encontrada", 404

    # Renderiza a página HTML com os detalhes da receita e ingredientes
    return render_template('templates/receita.html', receita=receita, ingredientes=ingredientes, user_info=user_info)


@app.route('/editar-nota/<int:id_receita>', methods=['POST'])
def editar_nota(id_receita):
    nova_nota = request.json.get('nota')
    # Lógica para atualizar a nota no banco de dados usando o ID da receita e a nova nota

    # Retorna uma resposta JSON (por exemplo, sucesso: True) para indicar o resultado da operação
    return jsonify(success=True)


@app.route("/", methods=['GET', 'POST'])
@login_required
def index():
    db = get_db()
    logo = 'images/livro_capa.png'
    # Obtém as informações do usuário atual
    user_info = g.user
    selected_category_ids = request.args.getlist('selected_category[]')
    selected_category = request.args.get("selected_category", "")

    selected_categories = []
    search_query = request.args.get("search", "")  # Obtém o critério de busca do parâmetro de consulta

    with db.cursor() as cursor:
        sql_livros = "SELECT * FROM livro"  # Substitua 'livros' pelo nome da sua tabela de livros
        cursor.execute(sql_livros)
        livros = cursor.fetchall()

    # Lógica para obter os nomes das categorias selecionadas do banco de dados
    with db.cursor() as cursor:
        for category_id in selected_category_ids:
            sql_category = "SELECT categoria FROM categoria_receita WHERE id_categoria = %s"
            cursor.execute(sql_category, (category_id,))
            category = cursor.fetchone()
            if category:
                selected_categories.append(category['categoria'])

    with db.cursor() as cursor:
        if search_query and selected_category:
            # Se ambas as consultas estiverem presentes, dividimos as categorias por vírgula e buscamos por cada uma
            categories = selected_category.split(",")  # Divide as categorias por vírgula
            placeholders = ', '.join(['%s'] * len(categories))  # Gera os placeholders para SQL
            sql_receita = f"SELECT * FROM receita WHERE nome LIKE %s AND categoria IN ({placeholders})"
            cursor.execute(sql_receita, (f"%{search_query}%",) + tuple(categories))
        elif search_query:
            sql_receita = "SELECT * FROM receita WHERE nome LIKE %s"
            cursor.execute(sql_receita, (f"%{search_query}%",))
        elif selected_category:
            categories = selected_category.split(",")  # Divide as categorias por vírgula
            placeholders = ', '.join(['%s'] * len(categories))  # Gera os placeholders para SQL
            sql_receita = f"SELECT * FROM receita WHERE categoria IN ({placeholders})"
            cursor.execute(sql_receita, tuple(categories))
        else:
            sql_receita = "SELECT * FROM receita"
            cursor.execute(sql_receita)

        receitas = cursor.fetchall()

    # Lógica para exibir as categorias selecionadas
    categories = []  # Substitua esta lista com suas categorias reais do banco de dados
    with db.cursor() as cursor:
        sql_categories = "SELECT categoria FROM categoria_receita"
        cursor.execute(sql_categories)
        categories = [category['categoria'] for category in cursor.fetchall()]

    return render_template('templates/livros.html', livros=livros, logo=logo, receitas=receitas, categories=categories, user_info=user_info, selected_categories=selected_categories)


# Lista vazia para armazenar as receitas inseridas dinamicamente
recipes = []

# Rota para atualizar o progresso da receita
@app.route('/atualizar-progresso/<int:card_index>', methods=['POST'])
def atualizar_progresso(card_index):
    novo_progresso = int(request.form['progress'])

    # Verifica se o índice da receita está dentro dos limites
    if 0 <= card_index < len(recipes):
        # Atualiza o progresso da receita correspondente
        recipes[card_index]['progress'] = novo_progresso

        # Aqui você deve salvar as alterações no progresso em algum armazenamento persistente (ex: banco de dados)

        # Retorna uma resposta para o frontend (confirmando o sucesso)
        return 'Progresso atualizado com sucesso'

    # Caso o índice esteja fora dos limites
    return 'Índice inválido para a receita', 400  # Retornando um erro 400 - Bad Request


@app.route("/remover-meta/<int:index>", methods=['POST'])
def remover_meta(index):
    if request.method == 'POST':
        try:
            # Verificar se o índice está dentro dos limites da lista de receitas
            if 0 <= index < len(recipes):
                # Remover a receita com base no índice fornecido
                del recipes[index]
                return 'Meta removida com sucesso'
            else:
                return 'Índice de meta inválido'
        except Exception as e:
            return f'Erro ao remover a meta: {str(e)}'

    return 'Método inválido para esta rota'


@app.route("/metas", methods=['GET', 'POST'])
def metas():
    user_info = g.user

    if request.method == 'POST':
        recipe_name = request.form['recipe_name']
        category = request.form['category']
        servings = int(request.form['servings'])
        meta_value = int(request.form['meta'])
        due_date = request.form['due_date']  # Obter a data de vencimento

        recipe = {
            'name': recipe_name,
            'category': category,
            'servings': servings,
            'progress': 0,
            'meta': meta_value,
            'due_date': due_date  # Adicionar a data de vencimento ao dicionário da receita
        }

        recipes.append(recipe)
        return redirect(url_for('metas'))  # Redireciona para a rota '/metas' para renderizar a página

    return render_template('templates/metas.html', recipes=recipes, user_info=user_info)


@app.route('/gerar_pdf/<int:livro_id>')
def gerar_pdf(livro_id):
    db = get_db()

    # Obter informações do livro
    with db.cursor() as cursor:
        sql_livro = "SELECT * FROM livro WHERE id_livro = %s"
        cursor.execute(sql_livro, (livro_id,))
        livro = cursor.fetchone()

        # Obter receitas selecionadas para o livro com detalhes dos ingredientes
        sql_receitas = """
            SELECT r.*, ir.quantidade, i.nome AS nome_ingrediente, m.sigla AS medida
            FROM livro_receita AS lr
            INNER JOIN receita AS r ON lr.receita_id = r.id_receita
            INNER JOIN ingredientes_receita AS ir ON r.id_receita = ir.id_receita
            INNER JOIN ingrediente AS i ON ir.id_ingrediente = i.id_ingrediente
            INNER JOIN medida AS m ON ir.id_medida = m.id_medida
            WHERE lr.livro_id = %s
        """

        with db.cursor() as cursor:
            cursor.execute(sql_receitas, (livro_id,))
            receitas = cursor.fetchall()

    # Gerar PDF
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)


    # Adicione informações ao PDF com destaque
    p.setFont("Helvetica-Bold", 14)  # Usando fonte negrito para destacar informações
    # Incluindo o logo
    logo_path = 'static/images/logo.png'  # Coloque o caminho para o logo aqui
    p.drawImage(logo_path, 100, 710, width=70, height=70, preserveAspectRatio=True)  # Ajuste conforme necessário

    p.drawString(100, 690, f'Título do Livro: {livro["titulo"]}')
    p.drawString(100, 670, f'Autor: {livro["autor"]}')
    p.setFont("Helvetica", 12)  # Volte à fonte padrão para o restante do conteúdo

    vertical_margin = 40  # Defina a margem vertical entre as receitas

    # Agrupar ingredientes por receita
    ingredientes_por_receita = defaultdict(list)
    for receita in receitas:
        ingredientes_por_receita[receita["nome"]].append(
            {
                "quantidade": receita["quantidade"],
                "medida": receita["medida"],
                "nome_ingrediente": receita["nome_ingrediente"]
            }
        )

    # Dentro do loop das receitas
    for nome_receita, ingredientes in ingredientes_por_receita.items():
        # Adiciona o nome da receita com espaçamento
        p.setFont("Helvetica-Bold", 16)
        y_position_nome_receita = 640
        p.drawString(100, y_position_nome_receita, f'Nome da Receita: {nome_receita}')
        p.setFont("Helvetica", 12)

        # Verifica se há uma imagem associada à receita atual
        caminho_imagem = None
        for receita_individual in receitas:
            if receita_individual["nome"] == nome_receita:
                caminho_relativo = receita_individual["imagem"]
                caminho_imagem = os.path.join("static", caminho_relativo)
                break
        else:
            # Se não houver correspondência, defina caminho_imagem como None
            caminho_imagem = None

        if caminho_imagem:
            try:
                # Defina a largura e altura desejadas
                largura_desejada = 350
                altura_desejada = 250

                # Carregue a imagem e obtenha suas dimensões originais
                imagem = ImageReader(caminho_imagem)
                largura_original, altura_original = imagem.getSize()

                # Calcule a proporção para manter as dimensões originais
                proporcao = min(largura_desejada / largura_original, altura_desejada / altura_original)

                # Calcule as novas dimensões da imagem
                largura_nova = largura_original * proporcao
                altura_nova = altura_original * proporcao

                # Calcule a posição y para centralizar verticalmente a imagem
                y_position_imagem = y_position_nome_receita - altura_nova - 20  # Adicione um espaçamento entre o nome da receita e a imagem

                # Desenhe a imagem no PDF
                p.drawImage(imagem, 100, y_position_imagem, width=largura_nova, height=altura_nova)
            except Exception as e:
                print(f"Erro ao adicionar imagem: {e}")

        # Adiciona a lista de ingredientes com espaçamento
        y_position_ingredientes = y_position_imagem - 30  # Adicione um espaçamento entre a imagem e a lista de ingredientes
        p.drawString(100, y_position_ingredientes, 'Ingredientes:')
        for i, ingrediente in enumerate(ingredientes):
            y_position_ingrediente = y_position_ingredientes - (
                        i + 1) * 15  # Ajuste a posição y para evitar sobreposição
            p.drawString(120, y_position_ingrediente,
                         f'- {ingrediente["nome_ingrediente"]} {ingrediente["quantidade"]} {ingrediente["medida"]}')

        # Adiciona porção
        y_position_porcao = y_position_ingredientes - len(ingredientes) * 15 - 20
        p.drawString(100, y_position_porcao, f'Porção: Serve {receitas[0]["qtde_porcao"]} pessoa(s)')

        # Adiciona modo de preparo dinâmico
        y_position_modo_preparo = y_position_porcao - 20
        x_position_modo_preparo = 100  # Defina a posição X inicial para o modo de preparo

        p.drawString(x_position_modo_preparo, y_position_modo_preparo, 'Modo de Preparo:')
        p.setFont("Helvetica", 12)

        # Separar o texto do modo de preparo em parágrafos
        modo_preparo_texto = receita_individual["modo_preparo"]
        paragrafos_modo_preparo = modo_preparo_texto.split('\n')

        # Limpar espaços em branco ou caracteres indesejados no final de cada parágrafo
        paragrafos_limpos = [paragrafo.rstrip() for paragrafo in paragrafos_modo_preparo]

        # Ajuste para a margem à direita apenas no modo de preparo
        x_position_texto = 120  # Defina a posição X para o texto do modo de preparo
        margem_direita_modo_preparo = 600  # Defina a margem à direita para o modo de preparo

        y_position_texto = y_position_modo_preparo - 20
        max_width_line = margem_direita_modo_preparo - x_position_texto

        for paragrafo in paragrafos_limpos:
            words = paragrafo.split()
            current_line = ''
            for word in words:
                word_width = p.stringWidth(word, "Helvetica", 12)
                if p.stringWidth(current_line + word, "Helvetica", 12) < max_width_line:
                    current_line += word + " "
                else:
                    p.drawString(x_position_texto, y_position_texto, current_line)
                    y_position_texto -= 15
                    current_line = word + " "
            p.drawString(x_position_texto, y_position_texto, current_line)
            y_position_texto -= 15

        # Adiciona espaço vertical entre as receitas
        p.showPage()

    p.save()

    buffer.seek(0)

    response = make_response(buffer.read())
    response.mimetype = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=Livro_{livro["titulo"]}.pdf'

    return response


@app.route("/receitas", methods=['GET', 'POST'])
@login_required
def receitas():
    db = get_db()
    # Obtém as informações do usuário atual
    user_info = g.user
    selected_category_ids = request.args.getlist('selected_category[]')
    selected_category = request.args.get("selected_category", "")

    selected_categories = []
    search_query = request.args.get("search", "")  # Obtém o critério de busca do parâmetro de consulta

    # Lógica para obter os nomes das categorias selecionadas do banco de dados
    with db.cursor() as cursor:
        for category_id in selected_category_ids:
            sql_category = "SELECT categoria FROM categoria_receita WHERE id_categoria = %s"
            cursor.execute(sql_category, (category_id,))
            category = cursor.fetchone()
            if category:
                selected_categories.append(category['categoria'])

    with db.cursor() as cursor:
        if search_query and selected_category:
            # Se ambas as consultas estiverem presentes, dividimos as categorias por vírgula e buscamos por cada uma
            categories = selected_category.split(",")  # Divide as categorias por vírgula
            placeholders = ', '.join(['%s'] * len(categories))  # Gera os placeholders para SQL
            sql_receita = f"SELECT * FROM receita WHERE nome LIKE %s AND categoria IN ({placeholders})"
            cursor.execute(sql_receita, (f"%{search_query}%",) + tuple(categories))
        elif search_query:
            sql_receita = "SELECT * FROM receita WHERE nome LIKE %s"
            cursor.execute(sql_receita, (f"%{search_query}%",))
        elif selected_category:
            categories = selected_category.split(",")  # Divide as categorias por vírgula
            placeholders = ', '.join(['%s'] * len(categories))  # Gera os placeholders para SQL
            sql_receita = f"SELECT * FROM receita WHERE categoria IN ({placeholders})"
            cursor.execute(sql_receita, tuple(categories))
        else:
            sql_receita = "SELECT * FROM receita"
            cursor.execute(sql_receita)

        receitas = cursor.fetchall()

    # Lógica para exibir as categorias selecionadas
    categories = []  # Substitua esta lista com suas categorias reais do banco de dados
    with db.cursor() as cursor:
        sql_categories = "SELECT categoria FROM categoria_receita"
        cursor.execute(sql_categories)
        categories = [category['categoria'] for category in cursor.fetchall()]

    return render_template('templates/receitas.html', receitas=receitas, categories=categories, user_info=user_info, selected_categories=selected_categories)


@app.route("/novo_livro", methods=["GET", "POST"])
@login_required
def novo_livro():
    db = get_db()
    user_info = g.user

    if request.method == "POST":
        titulo = request.form["titulo"]

        autor = request.form["autor"]
        receitas_selecionadas_ids = request.form.getlist("receitas[]")

        # Gerar um número de ISBN aleatório
        isbn = gerar_isbn()

        try:
            with db.cursor() as cursor:
                # Inserir o novo livro na tabela livro com o ISBN gerado
                sql_livro = "INSERT INTO livro (titulo, autor, isbn) VALUES (%s, %s, %s)"
                cursor.execute(sql_livro, (titulo, autor, isbn))
                livro_id = cursor.lastrowid  # Obtém o ID do livro recém-inserido

                # Associar as receitas marcadas ao livro
                for receita_id in receitas_selecionadas_ids:
                    sql_livro_receita = "INSERT INTO livro_receita (livro_id, receita_id) VALUES (%s, %s)"
                    cursor.execute(sql_livro_receita, (livro_id, receita_id))

            db.commit()

            flash("Novo livro criado com sucesso!", "success")
            return redirect(url_for("index"))
        except Exception as e:
            flash(f"Erro ao criar o novo livro: {str(e)}", "danger")
            print(e)
            return redirect(url_for("index"))

    # Obtém a lista de receitas do banco de dados
    with db.cursor() as cursor:
        sql_receitas = "SELECT * FROM receita"
        cursor.execute(sql_receitas)
        receitas = cursor.fetchall()

    # Obtém a lista de categorias do banco de dados
    with db.cursor() as cursor:
        sql_categorias = "SELECT * FROM categoria_receita"
        cursor.execute(sql_categorias)
        categorias = cursor.fetchall()

    return render_template("templates/inserts/novo_livro.html", user_info=user_info, receitas=receitas, categorias=categorias)


@app.route("/nova_receita", methods=["GET", "POST"])
@login_required
def nova_receita():
    db = get_db()
    user_info = g.user

    receita = {
        'nome': '',
        'modo_preparo': '',
        'qtde_porcao': ''
    }

    # Obtém a lista de ingredientes do banco de dados
    with db.cursor() as cursor:
        sql_ingredientes = "SELECT * FROM ingrediente"
        cursor.execute(sql_ingredientes)
        ingredientes = cursor.fetchall()

    # Obtém a lista de categorias do banco de dados
    with db.cursor() as cursor:
        sql_categorias = "SELECT * FROM categoria_receita"
        cursor.execute(sql_categorias)
        categorias = cursor.fetchall()

    # Obtém a lista de medidas do banco de dados
    with db.cursor() as cursor:
        sql_medidas = "SELECT * FROM medida"
        cursor.execute(sql_medidas)
        medidas = cursor.fetchall()

    if request.method == "POST":
        nome = request.form["nome"]
        modo_preparo = request.form["modo_preparo"]
        qtde_porcao = request.form["qtde_porcao"]
        ind_receita_inedita = request.form.get("ind_receita_inedita", 0)
        categorias_selecionadas_ids = request.form.getlist("categorias[]")
        ingredientes_selecionados_ids = request.form.getlist("ingredientes[]")
        quantidades_ingredientes = request.form.getlist("quantidades[]")
        # Remover valores vazios da lista quantidades_ingredientes
        quantidades_ingredientes = [qtd for qtd in quantidades_ingredientes if qtd.strip()]

        print(quantidades_ingredientes)
        medidas_ingredientes = request.form.getlist("medidas[]")
        imagem = request.files["imagem"]

        if imagem.filename != '':
            nome_arquivo = secure_filename(imagem.filename)
            caminho_arquivo = os.path.join(app.config["UPLOAD_FOLDER"], nome_arquivo)
            imagem.save(caminho_arquivo)
            caminho_arquivo = f'images/{nome_arquivo}'
        else:
            caminho_arquivo = 'images/default.jpg'

        categorias_selecionadas_nomes = []
        with db.cursor() as cursor:
            for categoria_id in categorias_selecionadas_ids:
                sql_categoria = "SELECT categoria FROM categoria_receita WHERE id_categoria = %s"
                cursor.execute(sql_categoria, (categoria_id,))
                categoria = cursor.fetchone()
                if categoria:
                    categorias_selecionadas_nomes.append(categoria["categoria"])

        categorias_string = ", ".join(categorias_selecionadas_nomes)
        try:
            with db.cursor() as cursor:
                # Inserir a nova receita na tabela receita
                sql_receita = "INSERT INTO receita (nome, categoria, modo_preparo, qtde_porcao, ind_receita_inedita, imagem, data_criacao) VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)"
                cursor.execute(sql_receita, (nome, categorias_string, modo_preparo, qtde_porcao, ind_receita_inedita, caminho_arquivo))
                receita_id = cursor.lastrowid  # Obtém o ID da receita recém-inserida

                for ingrediente_id, quantidade, medida_id in zip(ingredientes_selecionados_ids,
                                                                 quantidades_ingredientes, medidas_ingredientes):
                    # Verifica se a quantidade não está vazia ou consiste apenas de espaços em branco
                    if quantidade.strip():
                        print("Inserindo ingrediente:", ingrediente_id, quantidade, medida_id, receita_id)
                        sql_ingredientes_receita = "INSERT INTO ingredientes_receita (id_ingrediente, quantidade, id_medida, id_receita) VALUES (%s, %s, %s, %s)"
                        cursor.execute(sql_ingredientes_receita, (ingrediente_id, quantidade, medida_id, receita_id))
                    else:
                        print(
                            f"A quantidade do ingrediente {ingrediente_id} está vazia e não será adicionada à receita.")

            db.commit()

            flash("Nova receita criada com sucesso!", "success")
            return redirect(url_for("receitas"))  # Redireciona para a página de índice
        except Exception as e:
            flash(f"Erro ao criar a nova receita: {str(e)}", "danger")
            print(e)

    return render_template("templates/inserts/nova_receita.html", user_info=user_info, ingredientes=ingredientes, categorias=categorias, medidas=medidas, receita=receita)

@app.route('/novo_ingrediente', methods=['POST', 'GET'])
def novo_ingrediente():
    db = get_db()
    user_info = g.user

    ingrediente = {
        'nome': ''

    }

    if request.method == 'POST':
        nome = request.form['nome']


        sql = "INSERT INTO ingrediente (nome) VALUES (%s)"

        try:
            with db.cursor() as cursor:
                cursor.execute(sql, (nome))
                db.commit()
                return redirect(url_for('ingredientes_table'))
        except Exception as e:
            return str(e)
    return render_template('templates/inserts/novo_ingrediente.html', user_info=user_info, ingrediente=ingrediente)


@app.route('/novo_medida', methods=['POST', 'GET'])
def nova_medida():
    db = get_db()
    user_info = g.user

    medida = {
        'medida': '',
        'sigla': ''
    }

    if request.method == 'POST':
        nome = request.form['medida']
        descricao = request.form['sigla']

        sql = "INSERT INTO medida (medida, sigla) VALUES (%s, %s)"

        try:
            with db.cursor() as cursor:
                cursor.execute(sql, (nome, descricao))
                db.commit()
                return redirect(url_for('medidas_table'))
        except Exception as e:
            return str(e)
    return render_template('templates/inserts/nova_medida.html', user_info=user_info, medida=medida)


@app.route('/novo_cargo', methods=['POST', 'GET'])
def novo_cargo():
    db = get_db()
    user_info = g.user

    cargo = {
        'nome': '',
        'descricao': '',
        'data_inicio': '',
        'data_fim': '',
        'indicador_ativo': ''
    }

    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        data_inicio = request.form['data_inicio']
        data_fim = request.form['data_fim']
        if 'indicador_ativo' in request.form:
            indicador_ativo = int(request.form['indicador_ativo'])
        else:
            indicador_ativo = 0

        sql = "INSERT INTO cargo (nome, descricao, data_inicio, data_fim, indicador_ativo) VALUES (%s, %s, %s, %s, %s)"

        try:
            with db.cursor() as cursor:
                cursor.execute(sql, (nome, descricao, data_inicio, data_fim, indicador_ativo))
                db.commit()
                return redirect(url_for('cargos_table'))
        except Exception as e:
            return str(e)
    return render_template('templates/inserts/novo_cargo.html', user_info=user_info, cargo=cargo)


@app.route('/escolher_cargo/<int:cargo_id>', methods=['GET', 'POST'])
@login_required
def escolher_cargo(cargo_id):
    db = get_db()
    with db.cursor() as cursor:
        # Atualize o campo "cargo_id" do usuário na tabela de login com o cargo escolhido
        user_id = session['user_id']
        sql_update = "UPDATE login SET cargo_id = %s WHERE id = %s"
        cursor.execute(sql_update, (cargo_id, user_id))
        db.commit()

    # Redirecione o usuário de volta à página do perfil após escolher o cargo
    flash('Cargo escolhido com sucesso!', 'success')
    return redirect(url_for('usuario_page'))


@app.route('/novo_restaurante', methods=['POST', 'GET'])
def novo_restaurante():
    db = get_db()
    user_info = g.user

    restaurante = {
        'nome': '',
        'fantasia': '',
        'contato': ''
    }

    if request.method == 'POST':
        nome = request.form['nome']
        fantasia = request.form['fantasia']
        contato = request.form['contato']

        sql = "INSERT INTO restaurante (nome, fantasia, contato) VALUES (%s, %s, %s)"

        try:
            with db.cursor() as cursor:
                cursor.execute(sql, (nome, fantasia, contato))
                db.commit()
                return redirect(url_for('restaurantes_table'))
        except Exception as e:
            return str(e)
    return render_template('templates/inserts/novo_restaurante.html', user_info=user_info, restaurante=restaurante)

@app.route("/novo_funcionario", methods=['POST', 'GET'])
def novo_funcionario():
    db = get_db()
    user_info = g.user

    funcionario = {
        'nome': '',
        'rg': '',
        'data_ingresso': '',
        'salario': '',
        'nome_fantasia': ''
    }

    if request.method == 'POST':
        nome = request.form['nome']
        rg = request.form['rg']
        data_ingresso = request.form['data_ingresso']
        salario = request.form['salario']
        nome_fantasia = request.form['nome_fantasia']

        sql = "INSERT INTO funcionario (nome, rg,  data_ingresso, salario, nome_fantasia) VALUES (%s, %s, %s, %s, %s)"

        try:
            with db.cursor() as cursor:
                cursor.execute(sql, (nome, rg,  data_ingresso, salario, nome_fantasia))
                db.commit()
                return redirect(url_for('funcionarios_table'))
        except Exception as e:
            return str(e)
    return render_template('templates/inserts/novo_funcionario.html', user_info=user_info, funcionario=funcionario)

@app.route("/remover_cargo/<int:id>", methods=['POST'])
def remover_cargo(id):

    db = get_db()
    with db.cursor() as cursor:
        sql_delete = "DELETE FROM cargo WHERE id_cargo = %s"  # Ajuste o nome da coluna conforme necessário
        cursor.execute(sql_delete, (id,))
        db.commit()
    flash('Cargo removido com sucesso', 'success')
    return redirect(url_for('cargos_table'))


@app.route("/editar_cargo/<int:id>", methods=['GET', 'POST'])
def editar_cargo(id):
    db = get_db()
    # Obtém informações do usuário atual
    user_info = g.user

    # Lógica para obter o cargo com o ID fornecido do banco de dados
    with db.cursor() as cursor:
        sql_select_cargo = "SELECT * FROM cargo WHERE id_cargo = %s"
        cursor.execute(sql_select_cargo, (id,))
        cargo = cursor.fetchone()

    if request.method == 'POST':
        # Obtém os dados do formulário de edição
        nome = request.form['nome']
        descricao = request.form['descricao']
        data_inicio = request.form['data_inicio']
        data_fim = request.form['data_fim']
        indicador_ativo = request.form['indicador_ativo']

        # Atualiza o cargo no banco de dados
        with db.cursor() as cursor:
            sql_update_cargo = "UPDATE cargo SET nome=%s, descricao=%s, data_inicio=%s, data_fim=%s, indicador_ativo=%s WHERE id_cargo=%s"
            cursor.execute(sql_update_cargo, (nome, descricao, data_inicio, data_fim, indicador_ativo, id))
            db.commit()

        flash('Cargo atualizado com sucesso', 'success')
        return redirect(url_for('cargos_table'))

    return render_template('templates/inserts/novo_cargo.html', cargo=cargo, user_info=user_info)


@app.route("/remover_funcionario/<int:id>", methods=['POST'])
def remover_funcionario(id):
    db = get_db()
    with db.cursor() as cursor:
        sql_delete = "DELETE FROM funcionario WHERE id_funcionario = %s"
        cursor.execute(sql_delete, (id,))
        db.commit()
    flash('Funcionário removido com sucesso', 'success')
    return redirect(url_for('funcionarios_table'))


@app.route("/editar_funcionario/<int:id>", methods=['GET', 'POST'])
def editar_funcionario(id):
    db = get_db()
    user_info = g.user

    with db.cursor() as cursor:
        sql_select_funcionario = "SELECT * FROM funcionario WHERE id_funcionario = %s"
        cursor.execute(sql_select_funcionario, (id,))
        funcionario = cursor.fetchone()

    if request.method == 'POST':
        nome = request.form['nome']
        rg = request.form['rg']
        data_ingresso = request.form['data_ingresso']
        salario = request.form['salario']
        nome_fantasia = request.form['nome_fantasia']

        with db.cursor() as cursor:
            sql_update_funcionario = "UPDATE funcionario SET nome=%s, rg=%s, data_ingresso=%s, salario=%s, nome_fantasia=%s WHERE id_funcionario=%s"
            cursor.execute(sql_update_funcionario, (nome, rg, data_ingresso, salario, nome_fantasia, id))
            db.commit()

        flash('Funcionário atualizado com sucesso', 'success')
        return redirect(url_for('funcionarios_table'))

    return render_template('templates/inserts/novo_funcionario.html', funcionario=funcionario, user_info=user_info)


@app.route("/editar_restaurante/<int:id>", methods=['GET', 'POST'])
def editar_restaurante(id):
    db = get_db()
    user_info = g.user

    with db.cursor() as cursor:
        sql_select_restaurante = "SELECT * FROM restaurante WHERE id_restaurante = %s"
        cursor.execute(sql_select_restaurante, (id,))
        restaurante = cursor.fetchone()

    if request.method == 'POST':
        nome = request.form['nome']
        fantasia = request.form['fantasia']
        contato = request.form['contato']

        with db.cursor() as cursor:
            sql_update_restaurante = "UPDATE restaurante SET nome=%s, fantasia=%s, contato=%s WHERE id_restaurante=%s"
            cursor.execute(sql_update_restaurante, (nome, fantasia, contato, id))
            db.commit()

        flash('Restaurante atualizado com sucesso', 'success')
        return redirect(url_for('restaurantes_table'))

    return render_template('templates/inserts/novo_restaurante.html', restaurante=restaurante, user_info=user_info)


@app.route("/remover_restaurante/<int:id>", methods=['POST'])
def remover_restaurante(id):
    db = get_db()
    with db.cursor() as cursor:
        sql_delete = "DELETE FROM restaurante WHERE id_restaurante = %s"
        cursor.execute(sql_delete, (id,))
        db.commit()
    flash('Restaurante removido com sucesso', 'success')
    return redirect(url_for('restaurantes_table'))


@app.route("/remover_ingrediente/<int:id>", methods=['POST'])
def remover_ingrediente(id):
    db = get_db()
    with db.cursor() as cursor:
        sql_delete = "DELETE FROM ingrediente WHERE id_ingrediente = %s"
        cursor.execute(sql_delete, (id,))
        db.commit()
    flash('Ingrediente removido com sucesso', 'success')
    return redirect(url_for('ingredientes_table'))


@app.route("/remover_medida/<int:id>", methods=['POST'])
def remover_medida(id):
    db = get_db()

    with db.cursor() as cursor:
        try:
            # Primeiro, exclua as entradas associadas na tabela ingredientes_receita
            sql_delete_associacao = "DELETE FROM ingredientes_receita WHERE id_medida = %s"
            cursor.execute(sql_delete_associacao, (id,))

            # Em seguida, exclua a medida da tabela medida
            sql_delete_medida = "DELETE FROM medida WHERE id_medida = %s"
            cursor.execute(sql_delete_medida, (id,))

            db.commit()

            flash('Medida removida com sucesso', 'success')
        except Exception as e:
            db.rollback()  # Em caso de erro, faça um rollback para evitar alterações indevidas
            flash(f"Erro ao remover a medida: {str(e)}", 'danger')

    return redirect(url_for('medidas_table'))



@app.route("/editar_ingrediente/<int:id>", methods=['GET', 'POST'])
def editar_ingrediente(id):
    db = get_db()
    user_info = g.user

    # Obtém informações do ingrediente com o ID fornecido do banco de dados
    with db.cursor() as cursor:
        sql_select_ingrediente = "SELECT * FROM ingrediente WHERE id_ingrediente = %s"
        cursor.execute(sql_select_ingrediente, (id,))
        ingrediente = cursor.fetchone()

    if request.method == 'POST':
        # Obtém os dados do formulário de edição
        nome = request.form['nome']

        # Atualiza o ingrediente no banco de dados
        with db.cursor() as cursor:
            sql_update_ingrediente = "UPDATE ingrediente SET nome=%s WHERE id_ingrediente=%s"
            cursor.execute(sql_update_ingrediente, (nome, id))
            db.commit()

        flash('Ingrediente atualizado com sucesso', 'success')
        return redirect(url_for('ingredientes_table'))

    return render_template('templates/inserts/novo_ingrediente.html', ingrediente=ingrediente, user_info=user_info)


@app.route("/editar_medida/<int:id>", methods=['GET', 'POST'])
def editar_medida(id):
    db = get_db()
    user_info = g.user

    # Obtém informações do ingrediente com o ID fornecido do banco de dados
    with db.cursor() as cursor:
        sql_select_medida = "SELECT * FROM medida WHERE id_medida = %s"
        cursor.execute(sql_select_medida, (id,))
        medida = cursor.fetchone()

    if request.method == 'POST':
        # Obtém os dados do formulário de edição
        medida = request.form['medida']
        sigla = request.form['sigla']

        # Atualiza o ingrediente no banco de dados
        with db.cursor() as cursor:
            sql_update_ingrediente = "UPDATE medida SET medida=%s, sigla=%s WHERE id_medida=%s"
            cursor.execute(sql_update_ingrediente, (medida, sigla, id))
            db.commit()

        flash('Ingrediente atualizado com sucesso', 'success')
        return redirect(url_for('medidas_table'))

    return render_template('templates/inserts/nova_medida.html', medida=medida, user_info=user_info)


@app.route("/editar_receita/<int:id>", methods=['GET', 'POST'])
@login_required
def editar_receita(id):
    db = get_db()
    user_info = g.user

    # Obter os dados da receita a ser editada
    with db.cursor() as cursor:
        sql_select_receita = "SELECT * FROM receita WHERE id_receita = %s"
        cursor.execute(sql_select_receita, (id,))
        receita = cursor.fetchone()

    if not receita:
        flash('Receita não encontrada', 'error')
        return redirect(url_for('receitas'))  # Redirecionar para a lista de receitas

    # Obtém a lista de ingredientes do banco de dados
    with db.cursor() as cursor:
        sql_ingredientes = "SELECT * FROM ingrediente"
        cursor.execute(sql_ingredientes)
        ingredientes = cursor.fetchall()

    # Obtém a lista de categorias do banco de dados
    with db.cursor() as cursor:
        sql_categorias = "SELECT * FROM categoria_receita"
        cursor.execute(sql_categorias)
        categorias = cursor.fetchall()

    # Obtém a lista de medidas do banco de dados
    with db.cursor() as cursor:
        sql_medidas = "SELECT * FROM medida"
        cursor.execute(sql_medidas)
        medidas = cursor.fetchall()

    if request.method == "POST":
        nome = request.form["nome"]
        modo_preparo = request.form["modo_preparo"]
        qtde_porcao = request.form["qtde_porcao"]
        ind_receita_inedita = request.form.get("ind_receita_inedita", 0)
        categorias_selecionadas_ids = request.form.getlist("categorias[]")
        ingredientes_selecionados_ids = request.form.getlist("ingredientes[]")
        quantidades_ingredientes = request.form.getlist("quantidades[]")
        medidas_ingredientes = request.form.getlist("medidas[]")
        imagem = request.files["imagem"]

        # Lógica de atualização dos dados da receita no banco de dados
        try:
            with db.cursor() as cursor:
                # Atualizar os dados da receita na tabela receita
                sql_atualizar_receita = "UPDATE receita SET nome = %s, modo_preparo = %s, qtde_porcao = %s, ind_receita_inedita = %s WHERE id_receita = %s"
                cursor.execute(sql_atualizar_receita, (nome, modo_preparo, qtde_porcao, ind_receita_inedita, id))

                # Lógica de atualização dos ingredientes da receita
                sql_excluir_ingredientes = "DELETE FROM ingredientes_receita WHERE id_receita = %s"
                cursor.execute(sql_excluir_ingredientes, (id,))

                for ingrediente_id, quantidade, medida_id in zip(ingredientes_selecionados_ids,
                                                                 quantidades_ingredientes, medidas_ingredientes):
                    if quantidade.strip():
                        sql_inserir_ingredientes = "INSERT INTO ingredientes_receita (id_receita, id_ingrediente, quantidade, id_medida) VALUES (%s, %s, %s, %s)"
                        cursor.execute(sql_inserir_ingredientes, (id, ingrediente_id, quantidade, medida_id))
                    else:
                        flash(
                            f"A quantidade do ingrediente {ingrediente_id} está vazia e não será adicionada à receita.",
                            "warning")

            db.commit()

            flash("Receita e ingredientes atualizados com sucesso!", "success")
            return redirect(url_for("receitas"))  # Redireciona para a página de índice
        except Exception as e:
            flash(f"Erro ao atualizar a receita: {str(e)}", "danger")
            print(e)

    return render_template("templates/inserts/nova_receita.html", user_info=user_info, ingredientes=ingredientes,
                           categorias=categorias, medidas=medidas, receita=receita)


@app.route("/remover_receita/<int:id>", methods=['POST'])
def remover_receita(id):
    db = get_db()

    with db.cursor() as cursor:
        # Verificar e remover manualmente as entradas relacionadas em livro_receita
        sql_delete_livro_receita = "DELETE FROM livro_receita WHERE receita_id = %s"
        cursor.execute(sql_delete_livro_receita, (id,))

        # Agora, exclua a receita
        sql_delete_receita = "DELETE FROM receita WHERE id_receita = %s"
        cursor.execute(sql_delete_receita, (id,))

        db.commit()

    flash('Receita removida com sucesso', 'success')
    return redirect(url_for('receitas'))



@app.route("/remover_livro/<int:id>", methods=['POST'])
def remover_livro(id):
    db = get_db()

    with db.cursor() as cursor:
        # Primeiro, exclua as entradas associadas na tabela livro_receita (se necessário)
        sql_delete_associacao = "DELETE FROM livro_receita WHERE livro_id = %s"
        cursor.execute(sql_delete_associacao, (id,))

        # Em seguida, exclua o livro da tabela livro
        sql_delete_livro = "DELETE FROM livro WHERE id_livro = %s"
        cursor.execute(sql_delete_livro, (id,))

        db.commit()

    flash('Livro removido com sucesso', 'success')
    return redirect(url_for('index'))


@app.route('/nova_categoria_receita', methods=['POST', 'GET'])
def nova_categoria_receita():
    user_info = g.user
    if request.method == 'POST':
        descricao = request.form['descricao']
        categoria = request.form['categoria']

        db = get_db()
        with db.cursor() as cursor:
            cursor.execute('INSERT INTO categoria_receita (categoria, descricao) VALUES (%s, %s)',
                           (categoria, descricao))
            db.commit()

        flash('Categoria de receita criada com sucesso', 'success')
        return redirect(url_for('categorias_receitas_table'))

    return render_template('templates/inserts/nova_categoria_receita.html', user_info=user_info)


@app.route('/editar_categoria_receita/<int:id>', methods=['POST', 'GET'])
def editar_categoria_receita(id):
    user_info = g.user
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM categoria_receita WHERE id_categoria = %s', (id,))
    categoria = cursor.fetchone()

    if request.method == 'POST':
        categoria_nome = request.form['categoria']
        descricao = request.form['descricao']

        cursor.execute('UPDATE categoria_receita SET categoria=%s, descricao=%s WHERE id_categoria=%s',
                       (categoria_nome, descricao, id))
        db.commit()

        flash('Categoria de receita atualizada com sucesso!', 'success')
        return redirect(url_for('categorias_receitas_table'))

    return render_template('templates/inserts/nova_categoria_receita.html', categoria=categoria, user_info=user_info)


@app.route('/remover_categoria_receita/<int:id>', methods=['POST'])
def remover_categoria_receita(id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM categoria_receita WHERE id_categoria = %s', (id,))
    db.commit()

    flash('Categoria de receita removida com sucesso!', 'success')
    return redirect(url_for('categorias_receitas_table'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)