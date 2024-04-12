from anytree import Node, RenderTree


def build_tree(df_col):
    """
    Build a tree from a column of the dataframe.
    :param df_col: It is a column of the dataframe.
    :return: The root node of the tree
    """
    root = Node('Root')  # Create the root node

    # Create nodes for each element and store them in a dictionary
    nodes = {}
    for element in df_col:
        elements_multilabel = element.split(' $ ')
        for element_multilabel in elements_multilabel:
            elements = element_multilabel.split(' | ')
            parent = root
            for elem in elements:
                if elem not in nodes:
                    nodes[elem] = Node(elem, parent=parent)
                parent = nodes[elem]

    return root


def build_trees(df):
    """
    Build a tree for each column of the dataframe.
    :return: A dictionary with the trees for each column of the dataframe.
    """
    # Create trees for each column
    trees = {}
    for column in list(set(df.columns) - {'idInSource', 'database', '#portraitMedia.original', 'repository.keeper'}):
        trees[column.split('.')[0]] = build_tree(df[column].dropna())

    return trees


def print_trees(trees, count=None):
    """
    Print the tree structure for each column
    :param trees: It is a dictionary with the trees for each column of the dataframe.
    :param count: It is a dictionary with the count for each node of the tree.
    """
    for column, tree in trees.items():
        print(f"Tree for {column}:, number of total elements is {len(tree.descendants)}")
        for pre, _, node in RenderTree(tree):
            if count is None or node.name == 'Root':
                print(f"{pre}{node.name}")
            else:
                print(f"{pre}{node.name} => {count[column][node.name]}")
        print()