from tkinter import *
from tkinter import messagebox
import pyodbc

# Función para obtener nombres de columnas de la tabla y si son IDENTITY
def obtener_info_columnas(mydb, table_name):
    cursor = mydb.cursor()
    cursor.execute(f"""
        SELECT COLUMN_NAME, COLUMNPROPERTY(OBJECT_ID('{table_name}'), COLUMN_NAME, 'IsIdentity') AS IsIdentity
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = '{table_name}';
    """)
    columnas_info = cursor.fetchall()
    nombres_columnas = [columna[0] for columna in columnas_info]
    es_identity = {columna[0]: bool(columna[1]) for columna in columnas_info}
    return nombres_columnas, es_identity

# Función para mostrar la ventana y actualizar un registro
def final_show(mydb, table_name):
    def actualizar_fila():
        fila_id = var.get()
        if fila_id is not None:
            try:
                columnas, es_identity = obtener_info_columnas(mydb, table_name)
                valores_a_actualizar = []
                set_clauses = []

                for col in columnas:
                    if not es_identity.get(col):  # No incluir columnas IDENTITY
                        valor = entries[col].get()
                        valores_a_actualizar.append(valor)
                        set_clauses.append(f"[{col}] = ?")

                if not set_clauses:
                    messagebox.showinfo("Advertencia", "No hay columnas modificables en esta tabla.")
                    return

                set_clause = ', '.join(set_clauses)
                query = f"UPDATE {table_name} SET {set_clause} WHERE [{id_column}] = ?"
                valores_a_actualizar.append(fila_id)

                cursor = mydb.cursor()
                cursor.execute(query, valores_a_actualizar)
                mydb.commit()
                messagebox.showinfo("Éxito", "Registro actualizado exitosamente")
                the_show.destroy()
            except pyodbc.Error as ex:
                sqlstate = ex.args[0]
                if sqlstate == '42000' and "Cannot update identity column" in str(ex):
                    messagebox.showerror("ERROR", "No se puede modificar la columna de identidad.")
                else:
                    messagebox.showerror("ERROR", f"El error es: \n{ex}")
            except Exception as ex:
                messagebox.showerror("ERROR", f"El error es: \n{ex}")
        else:
            messagebox.showerror("ERROR", "Seleccione una fila para actualizar")

    cursor = mydb.cursor()
    cursor.execute(f"SELECT * FROM {table_name};")
    records = cursor.fetchall()
    columnas, es_identity = obtener_info_columnas(mydb, table_name)

    # Asumimos que la primera columna es el identificador
    id_column = columnas[0]

    the_show = Toplevel()
    the_show.title(f"Actualizar datos de {table_name}")
    the_show.iconbitmap("codigos/assets/BDICON.ico")

    # Crear Canvas y Scrollbar
    canvas = Canvas(the_show)
    scrollbar = Scrollbar(the_show, orient="vertical", command=canvas.yview)
    scrollable_frame = Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Colocar el Canvas y la Scrollbar en la ventana
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Mostrar columnas como encabezado
    encabezado_modificable = [col for col in columnas if not es_identity.get(col)]
    encabezado_completo = ', '.join(columnas)
    Label(scrollable_frame, text=encabezado_completo, font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=5)

    # Mostrar registros con Radiobutton para seleccionar la fila a actualizar
    var = IntVar()
    for i, record in enumerate(records, start=1):
        Radiobutton(scrollable_frame, text=record, variable=var, value=record[0], command=lambda r=record: mostrar_detalles(r)).grid(row=i, column=0, padx=10, pady=5)

    # Diccionario para almacenar los Entry widgets
    entries = {}

    # Función para mostrar los detalles en Entry widgets (solo para columnas no IDENTITY)
    def mostrar_detalles(record):
        for i, col in enumerate(columnas):
            if not es_identity.get(col):
                if col not in entries:
                    label = Label(scrollable_frame, text=col)
                    label.grid(row=len(records) + list(es_identity.values()).count(True) + list(es_identity.keys()).index(col) - list(es_identity.values())[:list(es_identity.keys()).index(col)].count(True) + 1, column=0, padx=10, pady=5)
                    entry = Entry(scrollable_frame)
                    entry.grid(row=len(records) + list(es_identity.values()).count(True) + list(es_identity.keys()).index(col) - list(es_identity.values())[:list(es_identity.keys()).index(col)].count(True) + 1, column=1, padx=10, pady=5)
                    entries[col] = entry
                entries[col].delete(0, END)
                entries[col].insert(0, record[i])
            elif col in entries:
                # Limpiar Entry si la columna se volvió IDENTITY
                entries[col].delete(0, END)
                entries[col].insert(0, "No modificable (IDENTITY)")
            elif col not in entries:
                label_identity = Label(scrollable_frame, text=f"{col} (No modificable)")
                label_identity.grid(row=len(records) + list(es_identity.keys()).index(col) + 1, column=0, columnspan=2, padx=10, pady=5)
                entries[col] = Entry(scrollable_frame, state="readonly") # Crear un Entry aunque sea readonly


    # Botón para confirmar la actualización
    Button(scrollable_frame, text="Actualizar", command=actualizar_fila).grid(row=len(records) + len(columnas) + 2, column=0, padx=10, pady=10)
    Button(scrollable_frame, text="Cancelar", command=the_show.destroy).grid(row=len(records) + len(columnas) + 2, column=1, padx=10, pady=10)

# Función principal para modificar registro
def modify(mydb):
    try:
        select_show = Toplevel()
        select_show.title("Seleccionar tabla para modificar")
        select_show.iconbitmap("codigos/assets/BDICON.ico")

        def confirmacion():
            table_name = table_var.get()
            select_show.destroy()
            final_show(mydb, table_name)

        mycursor = mydb.cursor()
        mycursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_NAME <> 'sysdiagrams';")
        tables = [table[0] for table in mycursor.fetchall()]

        if not tables:
            messagebox.showerror("ERROR", "No hay tablas disponibles para modificar.")
            return

        table_var = StringVar()
        table_var.set(tables[0])  # Set default value

        for table in tables:
            Radiobutton(select_show, text=table, variable=table_var, value=table).pack(anchor=W)

        Button(select_show, text="Confirmar", command=confirmacion).pack()

    except Exception as ex:
        messagebox.showerror("ERROR", f"El error es: \n{ex}")